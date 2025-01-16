from setuptools import setup, find_packages

setup(
    name='myspeech',
    version='0.1',
    packages=find_packages(),
    py_modules=['myspeech', 'myspeech_lib', 'myspeech_service'],
    install_requires=[
        'requests',
        'pyaudio',
        'webrtcvad',
        'numpy',
        'pyperclip',
        'pynput',
        'pyobjc-core',
        'pyobjc-framework-Cocoa',
        'pyobjc-framework-Quartz',
        'pyobjc-framework-ApplicationServices',
        'pyobjc',
        'pyobjc-framework-Accessibility',
    ],
    entry_points={
        'console_scripts': [
            'myspeech=myspeech:main',
            'myspeech_service=myspeech_service:main',
        ],
    },
)