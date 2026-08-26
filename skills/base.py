from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SkillResult:
    """Resultado devuelto por cualquier skill tras ejecutar una acción.

    success: si la acción se completó correctamente.
    message: texto en español, listo para que Jarvis lo diga/muestre.
    data: información estructurada opcional (ej: el id de un evento creado),
          por si otra parte del sistema necesita usarla sin re-parsear 'message'.
    """
    success: bool
    message: str
    data: dict | None = None


class Skill(ABC):
    """Contrato que toda skill de Jarvis debe cumplir."""

    @property
    @abstractmethod
    def intent_name(self) -> str:
        """Nombre del intent que esta skill maneja, ej: 'calendar'."""
        ...

    @property
    @abstractmethod
    def keywords(self) -> list[str]:
        """Palabras clave que el router usará para detectar este intent."""
        ...

    @abstractmethod
    def execute(self, parameters: dict) -> SkillResult:
        """Ejecuta la acción de la skill con los parámetros extraídos."""
        ...