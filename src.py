# -*- coding: utf-8 -*-
"""Core calculations for the pluviometric dashboard.

The Streamlit app keeps the user interface in app.py; this module keeps the
numerical logic reusable by tests and by downstream hydraulic apps.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Mapping, Sequence

import numpy as np


EULER_GAMMA = 0.5772


def hex_to_rgba(hex_color: str, opacity: float = 0.1) -> str:
    """Convert a HEX color to a Plotly rgba() string."""
    color = hex_color.lstrip("#")
    if len(color) == 6:
        r, g, b = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {opacity})"
    return hex_color


def _as_float_array(values: Iterable[float]) -> np.ndarray:
    data = np.array([float(v) for v in values if v is not None], dtype=float)
    data = data[np.isfinite(data)]
    if data.size < 3:
        raise ValueError("Servono almeno tre valori validi per la stima statistica.")
    return data


def parametri_gumbel(values: Iterable[float]) -> Dict[str, float]:
    """Return mean, sample standard deviation, alpha and u for Gumbel EVI."""
    data = _as_float_array(values)
    mean = float(data.mean())
    std = float(data.std(ddof=1))
    if std <= 0:
        raise ValueError("La deviazione standard deve essere positiva.")
    alpha = math.pi / (std * math.sqrt(6.0))
    u = mean - EULER_GAMMA / alpha
    return {"media": mean, "dev_std": std, "alpha": alpha, "u": u}


def gumbel_quantile(values: Iterable[float], tempo_ritorno: float) -> float:
    """Estimate rainfall depth for a return period with the Gumbel EVI model."""
    if tempo_ritorno <= 1:
        raise ValueError("Il tempo di ritorno deve essere maggiore di 1 anno.")
    params = parametri_gumbel(values)
    y_tr = -math.log(-math.log(1.0 - 1.0 / float(tempo_ritorno)))
    return params["u"] + y_tr / params["alpha"]


def regressione_cpp_loglog(durate_ore: Sequence[float],
                           altezze_mm: Sequence[float]) -> Dict[str, float]:
    """Fit h(t) = a * t^n on log-log axes."""
    if len(durate_ore) != len(altezze_mm):
        raise ValueError("Durate e altezze devono avere la stessa lunghezza.")
    if len(durate_ore) < 2:
        raise ValueError("Servono almeno due durate per stimare la CPP.")
    x = np.log(np.array(durate_ore, dtype=float))
    y = np.log(np.array(altezze_mm, dtype=float))
    if np.any(~np.isfinite(x)) or np.any(~np.isfinite(y)):
        raise ValueError("Durate e altezze devono essere positive e finite.")
    n, intercept = np.polyfit(x, y, 1)
    y_hat = n * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - float(y.mean())) ** 2))
    r2 = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot
    return {"a": float(math.exp(intercept)), "n": float(n), "r2": r2}


def cpp_gumbel(durate_ore: Sequence[float],
               serie_per_durata: Mapping[float, Iterable[float]],
               tempo_ritorno: float) -> Dict[str, object]:
    """Compute Gumbel rainfall depths and CPP coefficients for one Tr."""
    altezze = [gumbel_quantile(serie_per_durata[d], tempo_ritorno)
               for d in durate_ore]
    fit = regressione_cpp_loglog(durate_ore, altezze)
    return {
        "tempo_ritorno": float(tempo_ritorno),
        "durate_ore": [float(d) for d in durate_ore],
        "altezze_mm": [float(h) for h in altezze],
        **fit,
    }


def formule_cpp_base() -> List[Dict[str, str]]:
    return [
        {
            "Grandezza": "Curva di possibilita pluviometrica",
            "Formula": "h(t) = a * t^n",
            "Ruolo": "Trasforma le durate in altezze di progetto",
        },
        {
            "Grandezza": "Variabile ridotta di Gumbel",
            "Formula": "y_T = -ln(-ln(1 - 1/Tr))",
            "Ruolo": "Dipende dal tempo di ritorno scelto",
        },
        {
            "Grandezza": "Altezza di pioggia Gumbel",
            "Formula": "h_T = u + y_T / alpha",
            "Ruolo": "Stima l'altezza estrema per durata e Tr",
        },
        {
            "Grandezza": "Regressione CPP",
            "Formula": "ln(h) = ln(a) + n * ln(t)",
            "Ruolo": "Stima a e n dai punti h_T(t)",
        },
        {
            "Grandezza": "Intensita media",
            "Formula": "i = h / t",
            "Ruolo": "Input naturale per IdraulicaPiattaforma",
        },
    ]


def portata_manning_trapezoidale(tirante_m: float, base_m: float,
                                 scarpa_hv: float, ks: float,
                                 pendenza: float) -> Dict[str, float]:
    """Uniform-flow discharge for a trapezoidal channel using Strickler Ks."""
    if tirante_m <= 0 or base_m <= 0 or scarpa_hv < 0 or ks <= 0 or pendenza <= 0:
        raise ValueError("I parametri idraulici devono essere positivi.")
    area = tirante_m * (base_m + scarpa_hv * tirante_m)
    perimetro = base_m + 2.0 * tirante_m * math.sqrt(1.0 + scarpa_hv ** 2)
    raggio = area / perimetro
    portata = ks * area * (raggio ** (2.0 / 3.0)) * math.sqrt(pendenza)
    velocita = portata / area
    return {
        "tirante_m": tirante_m,
        "area_m2": area,
        "perimetro_m": perimetro,
        "raggio_idraulico_m": raggio,
        "portata_m3s": portata,
        "velocita_ms": velocita,
    }


def tirante_trapezoidale_bisezione(portata_m3s: float, base_m: float,
                                   scarpa_hv: float, ks: float,
                                   pendenza: float,
                                   h_min: float = 0.001,
                                   h_max: float = 30.0,
                                   max_iter: int = 100) -> Dict[str, float]:
    """Solve the normal depth of a trapezoidal channel by bisection."""
    if portata_m3s <= 0:
        raise ValueError("La portata deve essere positiva.")
    low = h_min
    high = h_max
    for _ in range(max_iter):
        mid = 0.5 * (low + high)
        q_mid = portata_manning_trapezoidale(
            mid, base_m, scarpa_hv, ks, pendenza
        )["portata_m3s"]
        if q_mid < portata_m3s:
            low = mid
        else:
            high = mid
    tirante = 0.5 * (low + high)
    result = portata_manning_trapezoidale(
        tirante, base_m, scarpa_hv, ks, pendenza
    )
    result["velocita_ms"] = portata_m3s / result["area_m2"]
    result["portata_m3s"] = portata_m3s
    return result


def formule_sezione_trapezoidale(risultato: Dict[str, float],
                                 base_m: float,
                                 scarpa_hv: float,
                                 ks: float,
                                 pendenza: float) -> List[Dict[str, str]]:
    return [
        {
            "Grandezza": "Area bagnata",
            "Formula": "A = h * (b + z*h)",
            "Valore": f"{risultato['area_m2']:.4f}",
            "Unita": "m2",
        },
        {
            "Grandezza": "Perimetro bagnato",
            "Formula": "P = b + 2*h*sqrt(1 + z^2)",
            "Valore": f"{risultato['perimetro_m']:.4f}",
            "Unita": "m",
        },
        {
            "Grandezza": "Raggio idraulico",
            "Formula": "R = A / P",
            "Valore": f"{risultato['raggio_idraulico_m']:.4f}",
            "Unita": "m",
        },
        {
            "Grandezza": "Portata Strickler",
            "Formula": "Q = Ks * A * R^(2/3) * sqrt(i)",
            "Valore": f"{risultato['portata_m3s']:.4f}",
            "Unita": "m3/s",
        },
        {
            "Grandezza": "Velocita media",
            "Formula": "V = Q / A",
            "Valore": f"{risultato['velocita_ms']:.4f}",
            "Unita": "m/s",
        },
        {
            "Grandezza": "Parametri adottati",
            "Formula": "b, z, Ks, i",
            "Valore": f"b={base_m:.3f}; z={scarpa_hv:.3f}; Ks={ks:.3f}; i={pendenza:.5f}",
            "Unita": "-",
        },
    ]
