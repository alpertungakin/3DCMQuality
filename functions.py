# -*- coding: utf-8 -*-
"""
Created on Mon Feb 19 12:29:22 2024

@author: alper
"""

import numpy as np

def getNormal(poly):
    #Newells method
    n = np.array([0.0, 0.0, 0.0])

    for i, v_curr in enumerate(poly):
        v_next = poly[(i+1) % len(poly),:]
        n[0] += (v_curr[1] - v_next[1]) * (v_curr[2] + v_next[2]) 
        n[1] += (v_curr[2] - v_next[2]) * (v_curr[0] + v_next[0])
        n[2] += (v_curr[0] - v_next[0]) * (v_curr[1] + v_next[1])

    norm = np.linalg.norm(n)
    if norm==0:
        normalised = np.array([0,0,0], dtype=np.float64)
    else:
        normalised = n/norm

    return list(normalised)