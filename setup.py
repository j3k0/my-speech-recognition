from setuptools import setup, find_packages

setup(
    name='myspeech',  # Updated package name
    version='0.1',
    packages=find_packages(),
    py_modules=['myspeech', 'myspeech_lib', 'myspeech_service'],  # Updated module names
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
            'myspeech=myspeech:main',  # Updated entry point
            'myspeech_service=myspeech_service:main',  # Updated entry point
        ],
    },
)