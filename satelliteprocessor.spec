# satelliteprocessor.spec
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files
datas = [
    ('assets/satellite_icon.ico', 'assets'),
    ('ml_models/checkpoints/net_g_45738.pth', 'ml_models/checkpoints'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'gportal',
    'paramiko',
    'h5py',
    'pyproj',
    'matplotlib.backends.backend_tkagg',
    'PIL._tkinter_finder',
    'torch',
    'torch.nn',
    'torch.nn.functional',
    'torchvision',
    'scipy.special._ufuncs_cxx',
    'scipy._lib.messagestream',
    'sklearn.utils._typedefs',
    'sklearn.neighbors._partition_nodes',
    'timm',
    'timm.layers',
]

# Add all ml_models submodules
hiddenimports.extend(collect_submodules('ml_models'))
hiddenimports.extend(collect_submodules('core'))
hiddenimports.extend(collect_submodules('gui'))
hiddenimports.extend(collect_submodules('utils'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SatelliteProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True if you want console window for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/satellite_icon.ico',
)