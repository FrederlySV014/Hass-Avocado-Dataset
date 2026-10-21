#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Punto de entrada principal para iniciar el servidor web del clasificador.
Enlazado a 127.0.0.1:5000.
"""

import os
import sys

# Asegurar path correcto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.app import run

if __name__ == "__main__":
    run()
