from setuptools import setup, find_packages

setup(
    name='whisper_groq',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pyaudio',
        'webrtcvad',
        'numpy',
    ],
    entry_points={
        'console_scripts': [
            'whisper_groq=whisper_groq:main',
        ],
    },
)