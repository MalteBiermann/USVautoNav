import Boot
import csv
import json
import Messgebiet
import random
import Sensoren
import sympy
import threading
import time
import matplotlib.pyplot as plt
plt.ion()

class Boot_Simulation(Boot.Boot):

    def __init__(self):

        super().__init__(self)
        ################################# S I M U L A T I O N ##########################################################
        #SIMULATIONSPARAMETER
        # Einlesen der Parameter aus JSON Datei
        datei = open("boot_init.json", "r")
        json_daten = json.load(datei)
        datei.close()

        xpos1_start_sim = json_daten["Boot"]["simulation_start_x"]
        ypos1_start_sim = json_daten["Boot"]["simulation_start_y"]
        self.position = Messgebiet.Punkt(xpos1_start_sim, ypos1_start_sim)
        self.heading = json_daten["Boot"]["simulation_start_heading"]
        self.suchbereich = json_daten["Boot"]["simulation_suchbereich"]

        # EINLESEN DES MODELLS ALS QUADTREE
        testdaten = open("Testdaten_DHM_Tweelbaeke.txt", "r", encoding='utf-8-sig')  # ArcGIS Encoding XD
        lines = csv.reader(testdaten, delimiter=";")
        id_testdaten = []
        x_testdaten = []
        y_testdaten = []
        tiefe_testdaten = []

        # Lesen der Datei
        for line in lines:
            id_testdaten.append(int(line[0]))
            x_testdaten.append(float(line[1]))
            y_testdaten.append(float(line[2]))
            tiefe_testdaten.append(float(line[3]))
        testdaten.close()

        testdaten_xmin = min(x_testdaten) - 10
        testdaten_xmax = max(x_testdaten) + 10
        testdaten_ymin = min(y_testdaten) - 10
        testdaten_ymax = max(y_testdaten) + 10

        xdiff = testdaten_xmax - testdaten_xmin
        ydiff = testdaten_ymax - testdaten_ymin
        xzentrum = testdaten_xmin + xdiff / 2
        yzentrum = testdaten_ymin + ydiff / 2

        # Einlesen der Testdaten
        initialrechteck = Messgebiet.Zelle(xzentrum, yzentrum, xdiff, ydiff)
        self.Testdaten_quadtree = Messgebiet.Uferpunktquadtree(initialrechteck)

        # Generieren des Quadtree
        for i in range(len(x_testdaten)):
            x = x_testdaten[i]
            y = y_testdaten[i]
            tiefe = tiefe_testdaten[i]

            p = Messgebiet.Bodenpunkt(x, y, tiefe)

            self.Testdaten_quadtree.punkt_einfuegen(p)

        # EINLESEN DES TEST POLYGONS
        testdaten_path = open("Testdaten_Polygon.txt", "r")
        lines = csv.reader(testdaten_path, delimiter=";")
        testdaten = []

        # Lesen der Datei
        for line in lines:
            testdaten.append(sympy.Point(tuple([float(komp) for komp in line])))
        testdaten_path.close()
        self.ufer_polygon = sympy.Polygon(*testdaten)

        ################################################################################################################
        ################################################################################################################

    # wird im self.akt_takt aufgerufen und überschreibt self.AktuelleSensordaten mit den neusten Sensordaten
    def Datenaktualisierung(self):

        if not self.auslesen:
            self.Sensorwerte_auslesen()

        self.fortlaufende_aktualisierung = True

        def Ueberschreibungsfunktion(self):

            Letzte_Bodenpunkte = []
            while self.fortlaufende_aktualisierung:

                ########## S I M U L A T I O N #############################################################

                self.AktuelleSensordaten[0].daten = Sensoren.Daten(0, [self.position.x, self.position.y, 0, 0, 4], time.time())

                gnss2 = self.Uferpunktberechnung(1)
                self.AktuelleSensordaten[1].daten = Sensoren.Daten(0, [gnss2.x, gnss2.y, 0, 0, 4], time.time())

                suchgebiet = Messgebiet.Zelle(self.position.x, self.position.y, self.suchbereich, self.suchbereich)
                tiefenpunkte = self.Testdaten_quadtree.abfrage(suchgebiet)

                tiefe = mean(tiefenpunkte)
                self.AktuelleSensordaten[2].daten = Sensoren.Daten(0, [tiefe, tiefe], time.time())

                p1, p2 = sympy.Point(self.position.x, self.position.y), sympy.Point(gnss2.x, gnss2.y)
                strahl = sympy.Line(p1, p2)
                schnitt = self.ufer_polygon.intersection(strahl)
                # Finden des Punkts, der das Ufer als erstes schneidet
                ufer_punkt = None
                diff = p2 - p1
                skalar = 100000
                for pkt in schnitt:
                    diff_pkt = pkt-p1
                    skalar_test = diff_pkt.x*diff.x + diff_pkt.y*diff.y
                    if skalar_test >= 0:
                        if skalar_test < skalar:
                            skalar = skalar_test
                            ufer_punkt = pkt
                distanz = ((ufer_punkt.x-p1.x)**2 + (ufer_punkt.y-p1.y)**2) ** 0.5
                distanz = random.gauss(distanz, 5)
                self.AktuelleSensordaten[3].daten = Sensoren.Daten(0, distanz, time.time())
                ###########################################################################################

                # Abgeleitete Daten berechnen und überschreiben

                # aktuelles Heading berechnen und zum Boot abspeichern
                if self.AktuelleSensordaten[0] and self.AktuelleSensordaten[1]:  # Headingberechnung
                    self.heading = self.Headingberechnung()

                # wenn ein aktueller Entfernungsmesswert besteht, soll ein Uferpunkt berechnet werden
                if self.AktuelleSensordaten[0] and self.AktuelleSensordaten[1] and self.AktuelleSensordaten[
                    3]:  # Uferpunktberechnung
                    self.uferpunkt = self.Uferpunktberechnung()
                    if self.Messgebiet != None:
                        Messgebiet.Uferpunkt_abspeichern(self.uferpunkt)

                # Tiefe berechnen und als Punktobjekt abspeichern (die letzten 10 Messwerte mitteln)
                if self.AktuelleSensordaten[0] and self.AktuelleSensordaten[2]:
                    Bodendaten = (self.AktuelleSensordaten[0], self.AktuelleSensordaten[2])
                    Letzte_Bodenpunkte.append(Bodendaten)

                    if len(Letzte_Bodenpunkte) > 10:
                        Bodenpunkt = self.Bodenpunktberechnung(Letzte_Bodenpunkte)
                        self.Bodenpunkte.append(Bodenpunkt)
                        if len(self.Bodenpunkte) > 2:
                            self.Bodenpunkte.pop(0)
                        # je nach Tracking Mode sollen die Median Punkte mitgeführt werden oder aus der Liste gelöscht werden (da sie ansonsten bei einem entfernt liegenden Profil mit berücksichtigt werden würden)
                        if self.tracking_mode.value < 2:
                            self.median_punkte.append(Bodenpunkt)
                        else:
                            self.median_punkte = []
                        Letzte_Bodenpunkte = []

                time.sleep(self.akt_takt)

        self.aktualisierungsprozess = threading.Thread(target=Ueberschreibungsfunktion, args=(self,), daemon=True)
        self.aktualisierungsprozess.start()

        time.sleep(0.1)
        if not self.PixHawk.homepoint:
            punkt = Messgebiet.Punkt(self.AktuelleSensordaten[0].daten[0], self.AktuelleSensordaten[0].daten[1])
            self.PixHawk.homepoint = punkt

    # TODO: evtl Rechteck abhängig von Geschw. oder direkt Rechteck um das Boot legen
    # TODO: toleranz muss auf die Pixhawk interne Toleranz passen (Pixhawk-Toleranz muss kleiner gleich toleranz sein)
    def Punkt_anfahren(self, punkt, geschw=2.0, toleranz=10):  # Utm-Koordinaten und Gechwindigkeit setzen
        self.PixHawk.Geschwindigkeit_setzen(geschw)
        self.PixHawk.Wegpunkt_anfahren(punkt.x, punkt.y)
        self.punkt_anfahren = True
        print("Fahre Punkt mit Koordinaten E:", punkt.x, "N:", punkt.y, "an")
        punkt_box = Messgebiet.Zelle(punkt.x, punkt.y, toleranz, toleranz)

        def punkt_anfahren_test(self):
            self.punkt_anfahren = True
            while self.punkt_anfahren:
                test = punkt_box.enthaelt_punkt(self.position)
                if test:
                    self.punkt_anfahren = False
                time.sleep(self.akt_takt)
        thread = threading.Thread(target=punkt_anfahren_test, args=(self, ), daemon=True)
        thread.start()


if __name__ == "__main__":
    # EINLESEN DES TEST POLYGONS
    testdaten_path = open("Testdaten_Polygon.txt", "r")
    lines = csv.reader(testdaten_path, delimiter=";")
    testdaten_poly = []

    # Lesen der Datei
    for line in lines:
        testdaten_poly.append(sympy.Point(tuple([float(komp) for komp in line])))
    testdaten_path.close()
    ufer_polygon = sympy.Polygon(*testdaten_poly)

    p1, p2 = sympy.Point(451914.7237857745, 26869983909136309080730271 / 4565964803450000000-2), sympy.Point(451914.7237857745, 26869983909136309080730271 / 4565964803450000000)
    line = sympy.Line(p1, p2)

    schnitt = line.intersection(ufer_polygon)

    # EINLESEN DES MODELLS ALS QUADTREE
    testdaten = open("Testdaten_DHM_Tweelbaeke.txt", "r", encoding='utf-8-sig')  # ArcGIS Encoding XD
    lines = csv.reader(testdaten, delimiter=";")
    id_testdaten = []
    x_testdaten = []
    y_testdaten = []
    tiefe_testdaten = []

    # Lesen der Datei
    for line in lines:
        id_testdaten.append(int(line[0]))
        x_testdaten.append(float(line[1]))
        y_testdaten.append(float(line[2]))
        tiefe_testdaten.append(float(line[3]))

    testdaten.close()
    figure, ax = plt.subplots()
    ax.plot([451914.7237857745, 451914.7237857745], [26869983909136309080730271 / 4565964803450000000-2, 26869983909136309080730271 / 4565964803450000000], lw=1)
    ax.scatter([x_testdaten], [y_testdaten])
    ax.plot()

    x=[]
    y=[]


    x_poly = []
    y_poly = []
    for polypunkt in testdaten_poly:
        x_poly.append(polypunkt.x)
        y_poly.append(polypunkt.y)



    schnitt_poly,=ax.plot([],[],marker='o',lw=0)

    ax.plot(x_poly,y_poly,lw=2)

    while True:

        for schnittpunkt in schnitt:
            x.append(schnittpunkt.x)
            y.append(schnittpunkt.y)

            schnitt_poly.set_xdata(x)
            schnitt_poly.set_ydata(y)

            plt.pause(0.5)



    i=0