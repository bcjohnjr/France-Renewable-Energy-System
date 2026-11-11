"""Schematic ERS corridors (lon, lat) drawn in Supplementary Fig. S3; not the GT1 alignment."""
import math

CORRIDORS = {  # schematic motorway corridors (lon, lat); NOT the GT1 alignment
    1: {'A1 Paris–Lille': [(2.35, 48.86), (2.78, 50.29), (3.06, 50.63)],
        'A25/A16 Lille–Dunkerque–Calais': [(3.06, 50.63), (2.37, 51.03), (1.86, 50.95)],
        'A6 Paris–Lyon': [(2.35, 48.86), (3.57, 47.80), (4.84, 47.02), (4.84, 45.76)],
        'A7 Lyon–Marseille': [(4.84, 45.76), (4.89, 44.93), (4.81, 44.14), (5.45, 43.53), (5.37, 43.30)],
        'A9 Orange–Le Perthus': [(4.81, 44.14), (4.36, 43.84), (3.88, 43.61), (3.00, 43.18), (2.90, 42.70), (2.86, 42.46)],
        'A10 Paris–Bordeaux': [(2.35, 48.86), (1.90, 47.90), (0.69, 47.39), (0.34, 46.58), (-0.46, 46.32), (-0.58, 44.84)],
        'A63 Bordeaux–Biriatou': [(-0.58, 44.84), (-1.10, 44.10), (-1.47, 43.49), (-1.74, 43.33)],
        'A4 Paris–Metz–Strasbourg': [(2.35, 48.86), (4.03, 49.26), (6.18, 49.12), (7.75, 48.58)],
        'A31 Luxembourg–Metz–Nancy–Beaune': [(6.13, 49.47), (6.18, 49.12), (6.18, 48.69), (5.33, 47.86), (5.04, 47.32), (4.84, 47.02)]},
    2: {'A61/A62 Bordeaux–Toulouse–Narbonne': [(-0.58, 44.84), (0.62, 44.20), (1.44, 43.60), (2.35, 43.21), (3.00, 43.18)],
        'A11 Paris–Le Mans–Nantes': [(2.35, 48.86), (1.49, 48.45), (0.20, 48.00), (-0.55, 47.47), (-1.55, 47.22)],
        'A13 Paris–Rouen–Caen / Le Havre': [(2.35, 48.86), (1.10, 49.44), (0.30, 49.33), (-0.37, 49.18)],
        'A29/A131 to Le Havre': [(0.30, 49.33), (0.11, 49.49)],
        'A8 Aix–Nice': [(5.45, 43.53), (6.15, 43.35), (6.75, 43.45), (7.26, 43.70)],
        'A36 Beaune–Mulhouse': [(4.84, 47.02), (6.02, 47.24), (7.34, 47.75)],
        'A20 Orléans–Limoges–Toulouse': [(1.90, 47.90), (1.69, 46.81), (1.26, 45.83), (1.53, 45.16), (1.44, 43.60)],
        'A26 Calais–Reims–Troyes': [(1.86, 50.95), (2.78, 50.29), (3.29, 49.85), (4.03, 49.26), (4.07, 48.30)],
        'A43 Lyon–Chambéry–Fréjus': [(4.84, 45.76), (5.92, 45.57), (6.69, 45.20)],
        'N165/A84 Nantes–Rennes–Brest': [(-1.55, 47.22), (-1.68, 48.11), (-2.76, 48.51), (-4.49, 48.39)],
        'A83/A837 Nantes–Niort–La Rochelle': [(-1.55, 47.22), (-0.46, 46.32), (-1.15, 46.16)],
        'A89 Bordeaux–Clermont–Lyon': [(-0.58, 44.84), (0.72, 45.18), (1.53, 45.16), (3.08, 45.78), (4.84, 45.76)],
        'A54/A55 Nîmes–Fos': [(4.36, 43.84), (4.94, 43.43), (5.37, 43.30)]},
}


def haversine_km(a, b):
    R = 6371.0
    l1, p1, l2, p2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def corridor_lengths(tortuosity=1.15):
    return [dict(tier=t, corridor=n, route_km=sum(haversine_km(p[i], p[i + 1]) for i in range(len(p) - 1)) * tortuosity)
            for t, cs in CORRIDORS.items() for n, p in cs.items()]
