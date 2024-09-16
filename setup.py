from setuptools import setup, find_packages

setup(
    name='whisper_groq',
    version='0.1',
    packages=find_packages(),
    py_modules=['whisper_groq', 'whisper_groq_lib', 'whisper_groq_service'],
    install_requires=[
        'requests',
        'pyaudio',
        'webrtcvad',
        'numpy',
        'pyperclip',
        'pynput',
    ],
    entry_points={
        'console_scripts': [
            'whisper_groq=whisper_groq:main',
            'whisper_groq_service=whisper_groq_service:main',
        ],
    },
)