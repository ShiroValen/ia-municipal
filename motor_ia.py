"""
=============================================================================
PROYECTO: IA Municipal · Priorización Inteligente
CURSO: Gestión de Proyectos TICs (EST315)
CLIENTE: Municipalidad de Lima (Simulado)
EQUIPO:
  - Project Manager: Cristian Ronaldo
  - Análisis de Datos: Ronald Wilder
  - Arquitectura IA: Yair Dilan
  - Comunicaciones: Choucha
ARCHIVO: motor_ia.py
DESCRIPCIÓN:
  Motor de priorización basado en ponderaciones multicriterio y reglas de
  negocio RN-01 a RN-08 para reportes de incidencias municipales.
=============================================================================
"""

import copy
from typing import Any, Dict, List, Tuple


# =============================================================================
# CONSTANTES DE PONDERACIÓN Y NORMALIZACIÓN
# =============================================================================
PESO_GRAVEDAD = 0.35
PESO_POBLACION = 0.30
PESO_TIEMPO = 0.20
PESO_RECURSOS = 0.15

MAX_GRAVEDAD = 5.0
MAX_POBLACION = 5000.0
MAX_TIEMPO_DIAS = 60.0

MAPA_RECURSOS = {
    "bajo": 100.0,
    "medio": 60.0,
    "alto": 30.0,
}


# =============================================================================
# FUNCIONES AUXILIARES Y VALIDACIÓN
# =============================================================================
def _texto(valor: Any, predeterminado: str = "") -> str:
    """Convierte un valor en texto seguro, quitando espacios externos."""
    if valor is None:
        return predeterminado
    return str(valor).strip()


def _numero(
    valor: Any,
    predeterminado: float,
    minimo: float = 0.0,
    maximo: float = float("inf"),
) -> float:
    """
    Convierte un valor a número y limita su rango.
    Si el valor no es numérico o no es finito, usa el valor predeterminado.
    """
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = predeterminado

    # Evita NaN e infinitos sin depender de comparaciones ambiguas con NaN.
    if numero != numero or numero in (float("inf"), float("-inf")):
        numero = predeterminado

    return min(maximo, max(minimo, numero))


def _estado_resuelto(reporte: Dict[str, Any]) -> bool:
    """Compara el estado sin distinguir mayúsculas ni espacios exteriores."""
    return _texto(reporte.get("estado")).casefold() == "resuelto"


def _clave_zona(reporte: Dict[str, Any]) -> Tuple[str, str]:
    return (
        _texto(reporte.get("distrito")),
        _texto(reporte.get("zona")),
    )


def _clave_duplicado(reporte: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        _texto(reporte.get("distrito")),
        _texto(reporte.get("zona")),
        _texto(reporte.get("categoria")),
    )


# =============================================================================
# NORMALIZACIÓN DE FACTORES
# =============================================================================
def normalizar_factores(reporte: Dict[str, Any]) -> Dict[str, float]:
    """
    Normaliza gravedad, población, tiempo y recursos a una escala de 0 a 100.
    Los datos ausentes o inválidos reciben valores predeterminados seguros.
    """
    gravedad = _numero(reporte.get("gravedad", 1), 1.0, 0.0, MAX_GRAVEDAD)
    poblacion = _numero(
        reporte.get("poblacion_afectada", 10), 10.0, 0.0, MAX_POBLACION
    )
    tiempo = _numero(
        reporte.get("tiempo_sin_resolver", 1), 1.0, 0.0, MAX_TIEMPO_DIAS
    )
    recursos = _texto(reporte.get("recursos_requeridos", "Medio"), "Medio").casefold()

    norm_gravedad = (gravedad / MAX_GRAVEDAD) * 100.0
    norm_poblacion = (poblacion / MAX_POBLACION) * 100.0
    norm_tiempo = (tiempo / MAX_TIEMPO_DIAS) * 100.0
    norm_recursos = MAPA_RECURSOS.get(recursos, MAPA_RECURSOS["medio"])

    return {
        "norm_gravedad": round(norm_gravedad, 2),
        "norm_poblacion": round(norm_poblacion, 2),
        "norm_tiempo": round(norm_tiempo, 2),
        "norm_recursos": round(norm_recursos, 2),
    }


# =============================================================================
# REGLAS CONTEXTUALES
# =============================================================================
def consolidar_duplicados(
    reportes: List[Dict[str, Any]],
) -> Dict[Tuple[str, str, str], List[Any]]:
    """
    Agrupa reportes activos por distrito, zona y categoría.
    Esta coincidencia indica similitud por esos campos; no confirma por sí sola
    que dos reportes describan exactamente el mismo incidente.
    """
    grupos: Dict[Tuple[str, str, str], List[Any]] = {}

    for reporte in reportes:
        if _estado_resuelto(reporte):
            continue

        clave = _clave_duplicado(reporte)
        grupos.setdefault(clave, []).append(reporte.get("id"))

    return grupos


def contar_concentracion_zonal(
    reportes: List[Dict[str, Any]],
) -> Dict[Tuple[str, str], int]:
    """Cuenta reportes activos por distrito y zona."""
    conteo: Dict[Tuple[str, str], int] = {}

    for reporte in reportes:
        if not _estado_resuelto(reporte):
            clave = _clave_zona(reporte)
            conteo[clave] = conteo.get(clave, 0) + 1

    return conteo


# =============================================================================
# CÁLCULO DEL RANKING
# =============================================================================
def calcular_ranking(reportes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calcula el ranking de priorización:
    1. Normaliza los cuatro factores.
    2. Aplica ponderaciones de 35 %, 30 %, 20 % y 15 %.
    3. Ejecuta las reglas de negocio RN-01 a RN-08.
    4. Limita el puntaje activo al intervalo [0, 100].
    5. Clasifica y ordena los reportes activos antes que los resueltos.
    """
    if not reportes:
        return []

    conteo_zonal = contar_concentracion_zonal(reportes)
    grupos_duplicados = consolidar_duplicados(reportes)
    reportes_procesados: List[Dict[str, Any]] = []

    for item in reportes:
        rep = copy.deepcopy(item)
        factores = normalizar_factores(rep)
        rep.update(factores)

        gravedad = _numero(rep.get("gravedad", 1), 1.0, 0.0, MAX_GRAVEDAD)
        poblacion = _numero(rep.get("poblacion_afectada", 0), 0.0)
        dias = _numero(rep.get("tiempo_sin_resolver", 0), 0.0)
        recursos = _texto(rep.get("recursos_requeridos", "Medio"), "Medio").casefold()
        categoria = _texto(rep.get("categoria"))
        es_resuelto = _estado_resuelto(rep)

        p_gravedad = factores["norm_gravedad"] * PESO_GRAVEDAD
        p_poblacion = factores["norm_poblacion"] * PESO_POBLACION
        p_tiempo = factores["norm_tiempo"] * PESO_TIEMPO
        p_recursos = factores["norm_recursos"] * PESO_RECURSOS

        puntaje_base = p_gravedad + p_poblacion + p_tiempo + p_recursos
        puntaje_final = puntaje_base
        reglas_aplicadas: List[Dict[str, str]] = []

        clave_zona = _clave_zona(rep)
        clave_dup = _clave_duplicado(rep)

        if not es_resuelto:
            # RN-01: Concentración zonal (3 o más reportes activos).
            cantidad_zonal = conteo_zonal.get(clave_zona, 0)
            if cantidad_zonal >= 3:
                bono_zonal = 7.0
                puntaje_final += bono_zonal
                reglas_aplicadas.append({
                    "codigo": "RN-01",
                    "nombre": "Concentración Zonal",
                    "impacto": f"+{bono_zonal} pts",
                    "detalle": (
                        f"Foco crítico detectado: {cantidad_zonal} reportes "
                        f"en {_texto(rep.get('distrito'), 'distrito')} "
                        f"({_texto(rep.get('zona'), 'zona')})."
                    ),
                })

            # RN-02: Coincidencias entre reportes activos.
            coincidentes = grupos_duplicados.get(clave_dup, [])
            if len(coincidentes) > 1:
                bono_dup = 5.0
                puntaje_final += bono_dup
                reglas_aplicadas.append({
                    "codigo": "RN-02",
                    "nombre": "Reincidencia / Reportes Similares",
                    "impacto": f"+{bono_dup} pts",
                    "detalle": (
                        f"Existen {len(coincidentes)} reportes activos con "
                        "el mismo distrito, zona y categoría."
                    ),
                })

            # RN-03: Antigüedad crítica (más de 30 días).
            if dias > 30:
                bono_antiguedad = 8.0
                puntaje_final += bono_antiguedad
                reglas_aplicadas.append({
                    "codigo": "RN-03",
                    "nombre": "Antigüedad Crítica",
                    "impacto": f"+{bono_antiguedad} pts",
                    "detalle": (
                        f"El problema acumula {int(dias)} días sin resolverse "
                        "(supera el umbral de 30 días)."
                    ),
                })

            # RN-04: Quick-win por requerir pocos recursos.
            if recursos == "bajo":
                bono_quickwin = 4.0
                puntaje_final += bono_quickwin
                reglas_aplicadas.append({
                    "codigo": "RN-04",
                    "nombre": "Optimización de Recursos",
                    "impacto": f"+{bono_quickwin} pts",
                    "detalle": (
                        "Resolución de bajo costo y alta factibilidad técnica "
                        "para despacho inmediato."
                    ),
                })

            # RN-05: Umbral de riesgo extremo.
            categoria_normalizada = categoria.casefold()
            es_emergencia = (
                (gravedad >= 5 and poblacion >= 1000)
                or (
                    categoria_normalizada in ("inundaciones", "fugas de agua")
                    and gravedad >= 5
                )
            )

            if es_emergencia:
                if puntaje_final < 85.0:
                    puntaje_final = 85.0
                    impacto_emergencia = "Fijado en mínimo 85 pts"
                else:
                    puntaje_final += 5.0
                    impacto_emergencia = "+5.0 pts (Emergencia)"

                reglas_aplicadas.append({
                    "codigo": "RN-05",
                    "nombre": "Umbral de Riesgo Extremo",
                    "impacto": impacto_emergencia,
                    "detalle": (
                        "Incidencia de severidad máxima que afecta a una "
                        "población numerosa o corresponde a una categoría "
                        "considerada crítica por la regla."
                    ),
                })

            # RN-06: Limitar puntaje al intervalo [0, 100].
            puntaje_acotado = min(100.0, max(0.0, puntaje_final))
            if puntaje_acotado != puntaje_final:
                reglas_aplicadas.append({
                    "codigo": "RN-06",
                    "nombre": "Límites de Puntaje",
                    "impacto": "Acotado [0-100]",
                    "detalle": (
                        "Puntaje ajustado al rango permitido de 0 a 100."
                    ),
                })
            puntaje_final = puntaje_acotado

            # RN-07: Clasificación por rangos.
            if puntaje_final >= 80.0:
                clasificacion = "Crítica"
            elif puntaje_final >= 65.0:
                clasificacion = "Alta"
            elif puntaje_final >= 45.0:
                clasificacion = "Media"
            else:
                clasificacion = "Baja"

            reglas_aplicadas.append({
                "codigo": "RN-07",
                "nombre": "Clasificación por Rango",
                "impacto": clasificacion,
                "detalle": (
                    f"Puntaje de {round(puntaje_final, 1)} pts asignado "
                    f"al segmento {clasificacion}."
                ),
            })

        else:
            # RN-08: Los reportes resueltos quedan inactivos.
            puntaje_final = 0.0
            clasificacion = "Baja"
            reglas_aplicadas.append({
                "codigo": "RN-08",
                "nombre": "Caso Resuelto",
                "impacto": "0 pts (Inactivo)",
                "detalle": (
                    "El reporte ya fue atendido y resuelto. Pasa a histórico "
                    "sin consumir prioridad activa."
                ),
            })

        rep["puntaje_base"] = round(puntaje_base, 2)
        rep["puntaje"] = round(puntaje_final, 2)
        rep["clasificacion"] = clasificacion
        rep["reglas_aplicadas"] = reglas_aplicadas
        rep["desglose_ponderado"] = {
            "gravedad_pts": round(p_gravedad, 2),
            "poblacion_pts": round(p_poblacion, 2),
            "tiempo_pts": round(p_tiempo, 2),
            "recursos_pts": round(p_recursos, 2),
        }
        rep["explicacion"] = generar_explicacion(rep)
        reportes_procesados.append(rep)

    # Los activos siempre aparecen primero; cada grupo se ordena por puntaje.
    reportes_procesados.sort(
        key=lambda r: (
            _estado_resuelto(r),
            -_numero(r.get("puntaje", 0), 0.0),
            -_numero(r.get("gravedad", 1), 1.0),
            -_numero(r.get("poblacion_afectada", 0), 0.0),
        )
    )

    for posicion, rep in enumerate(reportes_procesados, start=1):
        rep["ranking_posicion"] = posicion

    return reportes_procesados


# =============================================================================
# EXPLICACIÓN DEL RESULTADO
# =============================================================================
def generar_explicacion(reporte: Dict[str, Any]) -> str:
    """Genera una explicación legible de la prioridad calculada."""
    if _estado_resuelto(reporte):
        return (
            "Este reporte se encuentra en estado 'Resuelto'. Conforme a la "
            "regla RN-08, la incidencia pasa al histórico y su puntaje de "
            "prioridad activa se ajusta a 0.0 puntos."
        )

    puntaje = _numero(reporte.get("puntaje", 0), 0.0)
    clasificacion = _texto(reporte.get("clasificacion", "Baja"), "Baja")
    gravedad = _numero(reporte.get("gravedad", 1), 1.0)
    poblacion = _numero(reporte.get("poblacion_afectada", 0), 0.0)
    tiempo = _numero(reporte.get("tiempo_sin_resolver", 0), 0.0)
    recursos = _texto(reporte.get("recursos_requeridos", "Medio"), "Medio")
    categoria = _texto(reporte.get("categoria", "Incidencia"), "Incidencia")
    distrito = _texto(reporte.get("distrito", "el distrito"), "el distrito")
    zona = _texto(reporte.get("zona", "la zona"), "la zona")

    desglose = reporte.get("desglose_ponderado", {})
    p_grav = desglose.get("gravedad_pts", 0.0)
    p_pob = desglose.get("poblacion_pts", 0.0)
    p_tiempo = desglose.get("tiempo_pts", 0.0)
    p_rec = desglose.get("recursos_pts", 0.0)

    factores = {
        "Gravedad": p_grav,
        "Población": p_pob,
        "Tiempo de Espera": p_tiempo,
        "Viabilidad de Recursos": p_rec,
    }
    factor_mayor = max(factores, key=factores.get)

    reglas = reporte.get("reglas_aplicadas", [])
    codigos_especiales = {"RN-01", "RN-02", "RN-03", "RN-04", "RN-05"}
    reglas_especiales = [
        regla for regla in reglas
        if regla.get("codigo") in codigos_especiales
    ]

    explicacion = (
        f"El reporte de {categoria} en {distrito} (Zona {zona}) ha sido "
        f"clasificado con Prioridad {clasificacion.upper()} con un puntaje "
        f"final de {puntaje:.2f} / 100 puntos. El factor con mayor aporte "
        f"ponderado fue '{factor_mayor}'. Evaluación específica: gravedad "
        f"nivel {gravedad:g}/5 ({p_grav} pts ponderados), impacto directo "
        f"sobre {poblacion:,.0f} ciudadanos ({p_pob} pts), tiempo de espera "
        f"de {tiempo:g} días ({p_tiempo} pts) y recursos requeridos "
        f"'{recursos}' ({p_rec} pts). "
    )

    if reglas_especiales:
        codigos = ", ".join(regla["codigo"] for regla in reglas_especiales)
        detalles = "; ".join(
            f"{regla['codigo']} ({regla['nombre']}: {regla['impacto']})"
            for regla in reglas_especiales
        )
        explicacion += (
            f"Se activaron las siguientes reglas especiales ({codigos}): "
            f"{detalles}."
        )
    else:
        explicacion += (
            "No se activaron bonificaciones extraordinarias por las reglas "
            "RN-01 a RN-05."
        )

    return explicacion
