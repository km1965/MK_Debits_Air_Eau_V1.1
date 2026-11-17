# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/MK_PROJETS/MK_Debits_Air_Eau/debits_ae/main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:/MK_PROJETS/MK_Debits_Air_Eau/Calcul des debits points bas et  hauts.pdf', '.'), ('D:/MK_PROJETS/MK_Debits_Air_Eau/Note_Verification_195 et 13.39 Hydraulique_AEP compléte.docx', '.'), ('D:/MK_PROJETS/MK_Debits_Air_Eau/Verification_Evacuation_Air_AEP.docx', '.'), ('D:/MK_PROJETS/MK_Debits_Air_Eau/Note_Verification_Hydraulique_AEP_Complete.docx', '.'), ('D:/MK_PROJETS/MK_Debits_Air_Eau/PLAN_DEBIT_AIR_EAU.md', '.'), ('D:/MK_PROJETS/MK_Debits_Air_Eau/requirements.txt', '.'), ('D:/MK_PROJETS/MK_Debits_Air_Eau/assets/icon.ico', 'assets'), ('D:/MK_PROJETS/MK_Debits_Air_Eau/assets/icon.png', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MK_Debits_Air_Eau',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/MK_PROJETS/MK_Debits_Air_Eau/assets/icon.ico'],
)
