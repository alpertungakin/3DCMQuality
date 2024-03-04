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

def getTotalHeight(objct):
    totalHeight = 0
    if objct.get_vertices() == []:
        totalHeight = "None"
    else:
        vertices = np.array(objct.get_vertices())
        h_list = list(vertices[:,2])
        totalHeight = max(h_list) - min(h_list)
    return totalHeight

def flattenSubBounds(geometry):
    bound_list = []
    if len(geometry.boundaries) == 1:
        for b in geometry.boundaries[0]:
            bound_list = bound_list + b
    else:
        for b in geometry.boundaries:
            bound_list = bound_list + b
    return bound_list

def closeRing(bound_list):
    # ensure 103
    if abs(bound_list[0][0]-bound_list[-1][0])>0.01 and abs(bound_list[0][1]-bound_list[-1][1])>0.01 and abs(bound_list[0][2]-bound_list[-1][2])>0.01:
        bound_list.append(bound_list[0])
    else:
        pass
    return bound_list

def vertexCount(bound_list):
    # check 101
    return len(bound_list)

def duplicatePoints(bound_list):
    # check 102
    temp = bound_list[:-1]
    haveDups = False
    for i in range(len(temp)-1):
        if abs(temp[i][0]-temp[i+1][0])<0.01 and abs(temp[i][1]-temp[i+1][1])<0.01 and abs(temp[i][2]-temp[i+1][2])<0.01:
            haveDups = True
        else:
            continue
    return haveDups

def isClosed(bound_list):
    # check 103
    closeness = True
    if abs(bound_list[0][0]-bound_list[-1][0])>0.01 and abs(bound_list[0][1]-bound_list[-1][1])>0.01 and abs(bound_list[0][2]-bound_list[-1][2])>0.01:
        closeness = False
    return closeness

    
    