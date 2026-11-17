"""Génère l'icône de MK_Debits_Air_Eau (PNG 1024 px + ICO multi-tailles).

Dessin 100 % programmatique (Pillow), reproductible sans dépendance externe.
Exécution :
    python tools/generer_icone.py
"""

from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFilter

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "assets")
S = 1024

# Palette technique cohérente avec l'interface
NAVY_HAUT = (26, 52, 82, 255)
NAVY_BAS = (12, 26, 43, 255)
BADGE_HAUT = (34, 63, 97, 255)
BADGE_BAS = (17, 33, 53, 255)
ACIER = (150, 171, 192, 255)
ACIER_SOMBRE = (104, 124, 146, 255)
TEAL = (46, 196, 182, 255)
EAU_HAUT = (126, 227, 255, 255)
EAU_BAS = (13, 111, 203, 255)
BLANC = (255, 255, 255, 255)


def _degrade_vertical(taille: int, haut: tuple, bas: tuple) -> Image.Image:
    """Dégradé vertical RGBA."""
    img = Image.new("RGBA", (taille, taille))
    px = img.load()
    for y in range(taille):
        t = y / max(taille - 1, 1)
        couleur = tuple(int(haut[i] + (bas[i] - haut[i]) * t) for i in range(4))
        for x in range(taille):
            px[x, y] = couleur
    return img


def _mask_rectangle_arrondi(marge: int, rayon: int) -> Image.Image:
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [marge, marge, S - marge - 1, S - marge - 1], radius=rayon, fill=255
    )
    return mask


def _points_goutte(cx: float, cy: float, rayon: float) -> list[tuple[float, float]]:
    """Contour d'une goutte d'eau (pointe en haut, bas circulaire)."""
    d = 2.05 * rayon  # distance centre -> pointe
    beta = math.acos(rayon / d)
    pointe = (cx, cy - d)

    # Arc du côté droit vers le côté gauche en passant par le bas.
    phi_debut = -math.pi / 2 + beta  # tangente droite
    phi_fin = 3 * math.pi / 2 - beta  # tangente gauche
    points = [pointe]
    pas = 2.0 * math.pi / 180.0
    phi = phi_debut
    while phi <= phi_fin:
        points.append((cx + rayon * math.cos(phi), cy + rayon * math.sin(phi)))
        phi += pas
    points.append((cx + rayon * math.cos(phi_fin), cy + rayon * math.sin(phi_fin)))
    return points


def _dessiner_icone() -> Image.Image:
    # --- Fond : carré arrondi avec dégradé ---
    fond = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    marge = int(S * 0.045)
    masque_fond = _mask_rectangle_arrondi(marge, int(S * 0.225))
    fond = Image.composite(
        _degrade_vertical(S, NAVY_HAUT, NAVY_BAS),
        Image.new("RGBA", (S, S), (0, 0, 0, 0)),
        masque_fond,
    )

    dessin = ImageDraw.Draw(fond)

    # Liseré supérieur du cadre
    dessin.rounded_rectangle(
        [marge, marge, S - marge - 1, S - marge - 1],
        radius=int(S * 0.225),
        outline=(68, 104, 140, 190),
        width=max(2, int(S * 0.004)),
    )

    # --- Badge circulaire (section de conduite) ---
    cx, cy = S / 2.0, S * 0.51
    r_badge = S * 0.335
    boite = [cx - r_badge, cy - r_badge, cx + r_badge, cy + r_badge]

    masque_badge = Image.new("L", (S, S), 0)
    ImageDraw.Draw(masque_badge).ellipse(boite, fill=255)
    badge = Image.composite(
        _degrade_vertical(S, BADGE_HAUT, BADGE_BAS),
        Image.new("RGBA", (S, S), (0, 0, 0, 0)),
        masque_badge,
    )
    fond = Image.alpha_composite(fond, badge)
    dessin = ImageDraw.Draw(fond)

    # Anneau extérieur acier + anneau intérieur teal
    dessin.ellipse(boite, outline=ACIER, width=max(3, int(S * 0.011)))
    r_interne = S * 0.286
    dessin.ellipse(
        [cx - r_interne, cy - r_interne, cx + r_interne, cy + r_interne],
        outline=TEAL,
        width=max(2, int(S * 0.009)),
    )

    # Boulons de bride (8) sur la couronne
    r_boulons = S * 0.311
    r_boulon = S * 0.014
    for i in range(8):
        angle = math.radians(i * 45 + 22.5)
        bx = cx + r_boulons * math.cos(angle)
        by = cy + r_boulons * math.sin(angle)
        dessin.ellipse(
            [bx - r_boulon, by - r_boulon, bx + r_boulon, by + r_boulon],
            fill=ACIER_SOMBRE,
            outline=(190, 205, 219, 220),
            width=max(1, int(S * 0.002)),
        )

    # --- Goutte d'eau ---
    cx_g, cy_g = cx, S * 0.585
    r_g = S * 0.135
    points = _points_goutte(cx_g, cy_g, r_g)

    masque_goutte = Image.new("L", (S, S), 0)
    ImageDraw.Draw(masque_goutte).polygon(points, fill=255)

    degrade_eau = _degrade_vertical(S, EAU_HAUT, EAU_BAS)
    goutte = Image.composite(
        degrade_eau,
        Image.new("RGBA", (S, S), (0, 0, 0, 0)),
        masque_goutte,
    )
    fond = Image.alpha_composite(fond, goutte)
    dessin = ImageDraw.Draw(fond)

    # Reflet doux sur la goutte
    reflet = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d_reflet = ImageDraw.Draw(reflet)
    d_reflet.ellipse(
        [
            cx_g - r_g * 0.72,
            cy_g - r_g * 0.52,
            cx_g - r_g * 0.02,
            cy_g + r_g * 0.18,
        ],
        fill=(255, 255, 255, 70),
    )
    reflet = reflet.filter(ImageFilter.GaussianBlur(radius=S * 0.012))
    fond = Image.alpha_composite(fond, Image.composite(reflet, Image.new("RGBA", (S, S), (0, 0, 0, 0)), masque_goutte))
    dessin = ImageDraw.Draw(fond)

    # Bulles d'air dans la goutte
    bulles = [
        (cx_g - r_g * 0.28, cy_g + r_g * 0.16, r_g * 0.20),
        (cx_g + r_g * 0.30, cy_g - r_g * 0.18, r_g * 0.14),
        (cx_g - r_g * 0.06, cy_g - r_g * 0.48, r_g * 0.095),
    ]
    for bx, by, rb in bulles:
        dessin.ellipse(
            [bx - rb, by - rb, bx + rb, by + rb],
            fill=(255, 255, 255, 205),
        )
        dessin.ellipse(
            [bx - rb * 1.55, by - rb * 1.75, bx - rb * 0.35, by - rb * 0.55],
            fill=(255, 255, 255, 110),
        )

    # Petit arc lumineux en haut du badge
    arc = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d_arc = ImageDraw.Draw(arc)
    d_arc.arc(
        [cx - r_badge * 0.94, cy - r_badge * 0.94, cx + r_badge * 0.94, cy + r_badge * 0.94],
        start=203,
        end=337,
        fill=(255, 255, 255, 80),
        width=max(3, int(S * 0.010)),
    )
    arc = arc.filter(ImageFilter.GaussianBlur(radius=S * 0.006))
    fond = Image.alpha_composite(fond, arc)

    return fond


def main() -> None:
    os.makedirs(DOSSIER, exist_ok=True)
    icone = _dessiner_icone()

    chemin_png = os.path.join(DOSSIER, "icon.png")
    icone.save(chemin_png, "PNG")
    print("PNG :", chemin_png, icone.size)

    chemin_ico = os.path.join(DOSSIER, "icon.ico")
    tailles = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icone.save(chemin_ico, format="ICO", sizes=tailles)
    print("ICO :", chemin_ico)
    print("Tailles ICO :", ", ".join(f"{w}x{h}" for w, h in tailles))


if __name__ == "__main__":
    main()
