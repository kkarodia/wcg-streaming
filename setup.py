import setuptools
import os
import sys

try:
    import multiprocessing  # noqa
except ImportError:
    pass

# Determine PortAudio include and library paths
portaudio_include_paths = [
    "/usr/include/portaudio2",
    "/usr/include",
    "/usr/local/include"
]

portaudio_lib_paths = [
    "/usr/lib/x86_64-linux-gnu",
    "/usr/lib",
    "/usr/local/lib"
]

# Find the first existing path
def find_existing_path(paths):
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0]  # Default to first path if none exist

portaudio_include_path = find_existing_path(portaudio_include_paths)
portaudio_lib_path = find_existing_path(portaudio_lib_paths)

setuptools.setup(
    name='your_project_name',
    version='0.1',
    setup_requires=['pbr>=1.8'],
    pbr=True,
    install_requires=[
        'requests',
        'pyaudio',
    ],
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
