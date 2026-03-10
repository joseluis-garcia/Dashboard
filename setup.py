#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup tradicional para compatibilidad con herramientas legacy.
La configuración principal está en pyproject.toml (PEP 517/518).
"""

from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        packages=find_packages(),
        package_data={
            "dashboard": [
                "comun/icons/*.png",
                "py.typed",
            ],
        },
        include_package_data=True,
    )
