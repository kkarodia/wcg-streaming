import setuptools
import os

try:
    import multiprocessing  # noqa
except ImportError:
    pass

# Determine PortAudio include and library paths
portaudio_include_path = "/usr/include/portaudio2"
portaudio_lib_path = "/usr/lib/x86_64-linux-gnu"

# Check if paths exist, otherwise use system defaults
if not os.path.exists(portaudio_include_path):
    portaudio_include_path = "/usr/include"
if not os.path.exists(portaudio_lib_path):
    portaudio_lib_path = "/usr/lib"

setuptools.setup(
    setup_requires=['pbr>=1.8'],
    pbr=True,
    # Add extra compilation arguments for PyAudio
    ext_modules=[
        setuptools.Extension(
            'pyaudio._portaudio', 
            sources=[],  # PyAudio will handle sources
            include_dirs=[portaudio_include_path],
            library_dirs=[portaudio_lib_path],
            libraries=['portaudio'],
            extra_compile_args=[
                f"-I{portaudio_include_path}",
                f"-L{portaudio_lib_path}"
            ]
        )
    ]
)
