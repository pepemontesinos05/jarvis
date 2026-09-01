import io
import speech_recognition as sr
from faster_whisper import WhisperModel
from config.settings import WHISPER_MODEL_SIZE, WHISPER_COMPUTE_TYPE

_model = None


def _get_model() -> WhisperModel:
    """Carga el modelo Whisper una sola vez (es costoso) y lo reutiliza después."""
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type=WHISPER_COMPUTE_TYPE)
    return _model


def record_audio(timeout: int = 5, phrase_time_limit: int = 8):
    """Graba audio del micrófono hasta detectar silencio (o hasta los límites dados).
    Devuelve un AudioData de speech_recognition, o None si no se detectó voz a tiempo."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            return recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return None


def transcribe(audio_data) -> str | None:
    """Transcribe un AudioData a texto en español usando Whisper local.
    Devuelve None si no hay audio o la transcripción resulta vacía."""
    if audio_data is None:
        return None

    model = _get_model()
    wav_bytes = audio_data.get_wav_data()

    segments, _ = model.transcribe(io.BytesIO(wav_bytes), language="es")
    text = " ".join(segment.text for segment in segments).strip()
    return text or None