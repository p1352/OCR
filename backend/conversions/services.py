"""
Couche de service OCR interchangeable.

Le traitement réel est délégué à un *provider* implémentant
``extract_text`` et ``extract_table``. Le provider par défaut utilise
l'API Groq (compatible OpenAI Chat Completions) avec un modèle vision
(par ex. ``meta-llama/llama-4-scout-17b-16e-instruct``), qui accepte des
images encodées en base64 dans le message.

Limites connues :
- Le modèle vision peut produire des erreurs d'OCR ; le résultat n'est
  pas une garantie d'exactitude, d'où le contrôle humain obligatoire.
- Groq ne renvoie pas de score de confiance par caractère : le score
  calculé ici est une heuristique locale (voir ``compute_quality``),
  pas une mesure fiable de justesse.
- Si ``GROQ_API_KEY`` est absente, ``OCRServiceUnavailable`` est levée.
"""

import base64
import json
import time
from abc import ABC, abstractmethod

import requests
from django.conf import settings
from django.utils import timezone

from .models import Conversion, ExtractedTable, ExtractedText, QualityCheck


class OCRServiceUnavailable(Exception):
    """Le service OCR n'est pas configuré (clé manquante, etc.)."""


class OCRProviderError(Exception):
    """Erreur renvoyée par le fournisseur OCR."""


class BaseOCRProvider(ABC):
    name = "base"

    @abstractmethod
    def extract_text(self, image_path, mime_type):
        """Retourne {"text": str, "language": str, "raw": str}."""

    @abstractmethod
    def extract_table(self, image_path, mime_type):
        """Retourne {"headers": [...], "rows": [[...]], "raw": str}."""


class GroqVisionProvider(BaseOCRProvider):
    name = "groq"

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.url = settings.GROQ_API_URL
        self.timeout = settings.GROQ_TIMEOUT
        if not self.api_key:
            raise OCRServiceUnavailable(
                "GROQ_API_KEY n'est pas configurée. Renseignez-la dans le "
                "fichier .env pour activer la conversion d'images."
            )

    def _data_uri(self, image_path, mime_type):
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime_type};base64,{b64}"

    def _chat(self, image_path, mime_type, prompt):
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": self._data_uri(image_path, mime_type)},
                        },
                    ],
                }
            ],
            "temperature": 0,
        }
        if settings.GROQ_MAX_TOKENS > 0:
            payload["max_tokens"] = settings.GROQ_MAX_TOKENS
        try:
            resp = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise OCRProviderError(f"Erreur réseau vers Groq : {exc}") from exc
        if resp.status_code != 200:
            raise OCRProviderError(
                f"Groq a renvoyé HTTP {resp.status_code} : {resp.text[:500]}"
            )
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise OCRProviderError(f"Réponse Groq inattendue : {data}") from exc

    def extract_text(self, image_path, mime_type):
        prompt = (
            "Tu es un moteur OCR. Extrais tout le texte visible dans cette "
            "image, en préservant la structure (paragraphes, lignes). "
            "Réponds uniquement avec le texte extrait, sans commentaire. "
            "Sur la dernière ligne, ajoute 'LANG: xx' avec le code ISO de la "
            "langue principale détectée."
        )
        content = self._chat(image_path, mime_type, prompt)
        language = ""
        text = content
        for marker in ("\nLANG:", "LANG:"):
            if marker in content:
                idx = content.rfind(marker)
                language = content[idx + len(marker):].strip()[:20]
                text = content[:idx].rstrip() if marker.startswith("\n") else content
                if marker == "LANG:":
                    text = content[: idx].rstrip()
                break
        return {"text": text.strip(), "language": language, "raw": content}

    def extract_table(self, image_path, mime_type):
        prompt = (
            "Tu es un extracteur de tableaux. Analyse cette image et "
            "retourne le ou les tableaux qu'elle contient au format JSON "
            'strict : {"headers": ["col1", ...], "rows": [["v1", ...], ...]}. '
            "Chaque ligne doit avoir le même nombre de cellules que les "
            "en-têtes. Si aucun tableau n'est visible, retourne "
            '{"headers": [], "rows": []}. Réponds uniquement avec le JSON, '
            "sans balise markdown ni commentaire."
        )
        content = self._chat(image_path, mime_type, prompt)
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(cleaned[start : end + 1])
            else:
                raise OCRProviderError(
                    "Le modèle n'a pas renvoyé de tableau JSON exploitable."
                )
        headers = [str(h) for h in data.get("headers", [])]
        rows = [[str(c) for c in row] for row in data.get("rows", [])]
        rows = [r for r in rows if r]
        return {"headers": headers, "rows": rows, "raw": content}


def get_provider():
    """Fabrique le provider OCR actif. Interchangeable via cette fonction."""
    return GroqVisionProvider()


def compute_quality(conversion, result):
    """Heuristique locale de qualité — PAS une garantie d'exactitude.

    Produit un score 0-1 et des alertes à partir de signaux simples :
    résultat vide, très court, lignes de tableau incohérentes, etc.
    """
    alerts = []
    score = 1.0

    if conversion.conversion_type == Conversion.ConversionType.TEXT:
        text = (result or {}).get("text", "")
        n_chars = len(text.strip())
        if n_chars == 0:
            alerts.append("Aucun texte extrait : résultat vide.")
            score = 0.0
        elif n_chars < 10:
            alerts.append("Texte extrait très court (< 10 caractères).")
            score -= 0.4
        suspicious = sum(1 for c in text if c == "�" or ord(c) < 9)
        if suspicious:
            alerts.append(f"{suspicious} caractère(s) illisible(s) détecté(s).")
            score -= 0.3
        if not (result or {}).get("language"):
            alerts.append("Langue non détectée.")
            score -= 0.1
    else:
        headers = (result or {}).get("headers", [])
        rows = (result or {}).get("rows", [])
        if not headers and not rows:
            alerts.append("Aucun tableau détecté dans l'image.")
            score = 0.0
        else:
            bad = [i for i, r in enumerate(rows) if len(r) != len(headers)]
            if bad:
                alerts.append(
                    f"{len(bad)} ligne(s) ont un nombre de cellules "
                    "différent des en-têtes."
                )
                score -= 0.3
            if not headers:
                alerts.append("Tableau sans en-têtes détectées.")
                score -= 0.2
            if len(rows) <= 1:
                alerts.append("Tableau avec une seule ligne de données.")
                score -= 0.2

    return max(0.0, round(score, 2)), alerts


def run_conversion(conversion):
    """Exécute une conversion de bout en bout et enregistre les résultats."""
    image = conversion.image
    conversion.status = Conversion.Status.RUNNING
    image.status = image.ProcessingStatus.PROCESSING
    conversion.save(update_fields=["status"])
    image.save(update_fields=["status"])

    started = time.monotonic()
    try:
        provider = get_provider()
        if conversion.conversion_type == Conversion.ConversionType.TEXT:
            result = provider.extract_text(image.file.path, image.mime_type)
        else:
            result = provider.extract_table(image.file.path, image.mime_type)
        model_used = getattr(provider, "model", getattr(provider, "name", "inconnu"))
    except (OCRServiceUnavailable, OCRProviderError) as exc:
        conversion.status = Conversion.Status.FAILED
        conversion.error_message = str(exc)
        conversion.finished_at = timezone.now()
        conversion.duration_ms = int((time.monotonic() - started) * 1000)
        conversion.save()
        image.status = image.ProcessingStatus.FAILED
        image.save(update_fields=["status"])
        QualityCheck.objects.update_or_create(
            conversion=conversion,
            defaults={
                "confidence_score": 0.0,
                "alerts": [f"Échec du traitement : {exc}"],
            },
        )
        return conversion

    conversion.duration_ms = int((time.monotonic() - started) * 1000)
    conversion.finished_at = timezone.now()
    conversion.model_used = model_used
    conversion.raw_response = result.get("raw", "")
    conversion.status = Conversion.Status.DONE
    conversion.save()

    if conversion.conversion_type == Conversion.ConversionType.TEXT:
        ExtractedText.objects.update_or_create(
            conversion=conversion,
            defaults={
                "raw_text": result["text"],
                "language": result.get("language", ""),
            },
        )
    else:
        ExtractedTable.objects.update_or_create(
            conversion=conversion,
            defaults={"raw_data": {"headers": result["headers"], "rows": result["rows"]}},
        )

    score, alerts = compute_quality(conversion, result)
    QualityCheck.objects.update_or_create(
        conversion=conversion,
        defaults={"confidence_score": score, "alerts": alerts},
    )

    image.status = image.ProcessingStatus.DONE
    image.save(update_fields=["status"])
    return conversion
