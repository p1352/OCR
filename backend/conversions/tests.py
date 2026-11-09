import io
import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .models import Conversion, ExtractedTable, ExtractedText, QualityCheck, SourceImage
from .services import OCRServiceUnavailable, compute_quality, run_conversion

User = get_user_model()

MEDIA = tempfile.mkdtemp()


def png_bytes(size=(50, 20)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, "PNG")
    return buf.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class ImageUploadTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user(
            username="u", email="u@example.com", password="Str0ng!Pass"
        )
        self.api.force_authenticate(self.user)

    def upload(self, data=b"fake", name="x.png", content_type="image/png"):
        f = SimpleUploadedFile(name, data, content_type=content_type)
        return self.api.post("/api/images/", {"file": f}, format="multipart")

    def test_valid_png_upload(self):
        resp = self.upload(png_bytes())
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["mime_type"], "image/png")
        self.assertEqual(resp.data["width"], 50)

    def test_rejects_non_image(self):
        resp = self.upload(b"not an image at all")
        self.assertEqual(resp.status_code, 400)

    def test_rejects_mime_spoofing(self):
        # Extension .png mais contenu JPEG : le type déclaré n'est pas cru.
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, "JPEG")
        resp = self.upload(buf.getvalue(), name="x.png")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["mime_type"], "image/jpeg")


class FakeProvider:
    model = "fake-model"

    def extract_text(self, path, mime):
        return {"text": "Bonjour le monde", "language": "fr", "raw": "raw"}

    def extract_table(self, path, mime):
        return {"headers": ["A", "B"], "rows": [["1", "2"]], "raw": "raw"}


@override_settings(MEDIA_ROOT=MEDIA)
class ConversionFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user(
            username="u", email="u@example.com", password="Str0ng!Pass"
        )
        self.api.force_authenticate(self.user)
        self.image = SourceImage.objects.create(
            file=SimpleUploadedFile("i.png", png_bytes(), content_type="image/png"),
            original_name="i.png", mime_type="image/png",
            size_bytes=100, uploaded_by=self.user,
        )

    def test_text_conversion_end_to_end(self):
        with patch("conversions.services.get_provider", return_value=FakeProvider()):
            resp = self.api.post(f"/api/images/{self.image.pk}/convert/", {"type": "text"})
        self.assertEqual(resp.status_code, 201)
        conv = Conversion.objects.get(pk=resp.data["id"])
        self.assertEqual(conv.status, "done")
        self.assertEqual(conv.extracted_text.raw_text, "Bonjour le monde")
        self.assertEqual(conv.extracted_text.language, "fr")
        self.assertEqual(conv.quality_check.confidence_score, 1.0)

    def test_table_conversion_and_csv_export(self):
        with patch("conversions.services.get_provider", return_value=FakeProvider()):
            resp = self.api.post(f"/api/images/{self.image.pk}/convert/", {"type": "table"})
        conv = Conversion.objects.get(pk=resp.data["id"])
        self.assertEqual(conv.extracted_table.raw_data["headers"], ["A", "B"])

        resp = self.api.get(f"/api/conversions/{conv.pk}/export_csv/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("A,B", resp.content.decode())

    def test_xlsx_export(self):
        from openpyxl import load_workbook
        with patch("conversions.services.get_provider", return_value=FakeProvider()):
            self.api.post(f"/api/images/{self.image.pk}/convert/", {"type": "table"})
        conv = Conversion.objects.first()
        resp = self.api.get(f"/api/conversions/{conv.pk}/export_xlsx/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("spreadsheetml", resp["Content-Type"])
        ws = load_workbook(io.BytesIO(resp.content)).active
        self.assertEqual([c.value for c in ws[1]], ["A", "B"])
        self.assertEqual([c.value for c in ws[2]], ["1", "2"])

    def test_correction_and_decision(self):
        with patch("conversions.services.get_provider", return_value=FakeProvider()):
            self.api.post(f"/api/images/{self.image.pk}/convert/", {"type": "text"})
        conv = Conversion.objects.first()

        resp = self.api.patch(
            f"/api/conversions/{conv.pk}/text/",
            {"corrected_text": "Bonjour, le monde !"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["corrected_text"], "Bonjour, le monde !")

        resp = self.api.post(
            f"/api/conversions/{conv.pk}/decide/",
            {"decision": "validated", "comment": "OK"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        conv.refresh_from_db()
        self.assertEqual(conv.quality_check.decision, "validated")
        self.assertEqual(conv.quality_check.decided_by, self.user)
        self.assertEqual(conv.extracted_text.validation_status, "validated")

    def test_failed_conversion_without_api_key(self):
        with override_settings(GROQ_API_KEY=""):
            resp = self.api.post(f"/api/images/{self.image.pk}/convert/", {"type": "text"})
        conv = Conversion.objects.get(pk=resp.data["id"])
        self.assertEqual(conv.status, "failed")
        self.assertIn("GROQ_API_KEY", conv.error_message)
        self.assertTrue(conv.quality_check.alerts)

    def test_invalid_type_rejected(self):
        resp = self.api.post(f"/api/images/{self.image.pk}/convert/", {"type": "nope"})
        self.assertEqual(resp.status_code, 400)

    def test_table_correction(self):
        with patch("conversions.services.get_provider", return_value=FakeProvider()):
            self.api.post(f"/api/images/{self.image.pk}/convert/", {"type": "table"})
        conv = Conversion.objects.first()
        resp = self.api.patch(
            f"/api/conversions/{conv.pk}/table/",
            {"corrected_data": {"headers": ["A", "B"], "rows": [["9", "8"]]}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        conv.extracted_table.refresh_from_db()
        self.assertEqual(conv.extracted_table.final_data["rows"], [["9", "8"]])


class QualityHeuristicTests(TestCase):
    def test_empty_text_scores_zero(self):
        conv = Conversion(conversion_type="text")
        score, alerts = compute_quality(conv, {"text": "", "language": "fr"})
        self.assertEqual(score, 0.0)
        self.assertTrue(alerts)

    def test_inconsistent_rows_alerted(self):
        conv = Conversion(conversion_type="table")
        score, alerts = compute_quality(
            conv, {"headers": ["a", "b"], "rows": [["1", "2"], ["only-one"]]}
        )
        self.assertLess(score, 1.0)
        self.assertTrue(any("cellules" in a for a in alerts))
