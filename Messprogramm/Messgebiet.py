import Sensoren
import numpy

# Berechnet die Fläche des angeg. Polygons
# https://en.wikipedia.org/wiki/Shoelace_formula
# https://stackoverflow.com/questions/24467972/calculate-area-of-polygon-given-x-y-coordinates
def Flächenberechnung(x, y):
    """
    :param x, y: sind numpy-arrays
    :return:
    """
    # dot: Skalarprodukt, roll: nimmt das array und verschiebt alle Werte um den angeg. Index nach vorne
    return 0.5 * numpy.abs(numpy.dot(x, numpy.roll(y, 1)) - numpy.dot(y, numpy.roll(x, 1)))

class Punkt:

    id = 0

    def __init__(self, x, y, z=None):
        self.id = Punkt.id
        Punkt.id += 1
        self.x = x
        self.y = y
        if z:
            self.z = z
        self.zelle = self.Zellenzugehoerigkeit()

    def Zellenzugehoerigkeit(self):

        # gibt Rasterzelle des Punktes wieder; größe der Rasterzellen muss bekannt sein
        # oder Liste aller Rasterzellen iterieren und Methode enthaelt_punkt() verwenden
        pass


class Uferpunkt(Punkt):

    def __init__(self, x, y, z=None):
        super().__init__(x,y,z)


class Bodenpunkt(Punkt):

    def __init__(self, x, y, z, Sedimentstaerke= None):    # z muss angegeben werde, da Tiefe wichtg; Sedimentstaerke berechnet sich aus Differenz zwischen tiefe mit niedriger und hoher Messfrequenz
        super().__init__(x, y, z)
        self.Sedimentstaerke = Sedimentstaerke


class Zelle:

    def __init__(self,cx, cy, w, h):    # Rasterzelle mit mittelpunkt, weite und Höhe definieren, siehe
        self.cx, self.cy = cx, cy
        self.w, self.h = w, h
        self.west_kante, self.ost_kante = cx - w/2, cx + w/2
        self.nord_kante, self.sued_kante = cy - h/2, cy + h/2

        self.beinhaltet_uferpunkte = False
        self.beinhaltet_bodenpunkte = False

    def ebenenausgleichung(self):
        pass

    def enthaelt_punkt(self,Punkt):

        Punktart = type(Punkt).__name__
        punkt_x, punkt_y = Punkt.x, Punkt.y

        # Abfrage ob sich Punkt im Recheck befindet
        enthaelt_punkt = (punkt_x >= self.west_kante and punkt_x <  self.ost_kante and punkt_y >= self.nord_kante and punkt_y < self.sued_kante)


        if Punktart == "Uferpunkt": self.beinhaltet_uferpunkte = True
        if Punktart == "Bodenpunkt": self.beinhaltet_bodenpunkte = True

        return enthaelt_punkt           # Gibt True oder False zurück


class Profil:

    # Richtung: Kursrichtung in Gon (im Uhrzeigersinn); stuetzpunkt: Anfangspunkt bei start_lambda=0; start_lambda:
    # end_lmbda ist bei den verdichtenden Profilen gegeben
    def __init__(self, richtung, stuetzpunkt, start_lambda=0, end_lambda=None):
        self.richtung = numpy.array([numpy.sin(richtung*numpy.pi/200), numpy.cos(richtung*numpy.pi/200)]) # 2D Richtungsvektor in Soll-Fahrtrichtung
        self.stuetzpunkt = stuetzpunkt # Anfangspunkt, von dem die Profilmessung startet, wenn start_lambda=0
        self.lamb = start_lambda # aktuelles Lambda der Profilgeraden (da self.richtung normiert, ist es gleichzeitig die Entfernung vom Stuetzpunkt)
        self.start_lambda = start_lambda
        self.end_lambda = end_lambda
        self.aktuelles_profil = True # bei False ist diese Profil bereits gemessen worden
        self.ist_sternprofil = (self.end_lambda is None) # explizit testen, dass es nicht None ist, da es auch 0 sein kann (was als False interpretiert wird)

    # sollte während der Erkundung für das aktuelle Profil immer aufgerufen werden!!!
    def BerechneLambda(self, punkt):
        self.lamb = numpy.dot((punkt - self.stuetzpunkt), self.richtung)

    # Berechnet einen neuen Kurspunkt von aktuellem Lambda in 50m Entfernung (länge der Fahrtrichtung) und quer dazu (in Fahrtrichtung rechts ist positiv)
    def BerechneNeuenKurspunkt(self, laengs_entfernung=50, quer_entfernung=0):
        quer_richtung = numpy.array([self.richtung[1], -self.richtung[0]])
        punkt = self.stuetzpunkt + (self.lamb + laengs_entfernung) * self.richtung + quer_entfernung * quer_richtung
        return punkt

    # aktuell gefahrenen Profillänge
    def Profillaenge(self):
        return self.lamb - self.start_lambda

    # Punkt muss mind. Toleranz Meter auf dem Profil liegen für return True
    def PruefPunktAufProfil(self, punkt, toleranz=2):
        abstand = abstand_punkt_gerade(self.richtung, self.stuetzpunkt, punkt)
        return abs(abstand) < toleranz

    # prüft, ob ein geg Punkt innerhalb des Profils liegt (geht nur, wenn self.aktuelles_profil = False ODER wenn self.end_lambda != None
    def PruefPunktInProfil(self, punkt, profilbreite=5):
        if (not self.aktuelles_profil) or (self.end_lambda is not None):
            if self.PruefPunktAufProfil(punkt, profilbreite):
                lamb = numpy.dot(self.richtung, (punkt - self.stuetzpunkt))
                return self.start_lambda <= lamb <= self.end_lambda
            else:
                return False

    # Überprüft, ob das Profil, das aus den Argumenten initialisiert werden KÖNNTE, ähnlich zu dem self Profil ist (unter Angabe der Toleranz)
    # Toleranz ist das Verhältnis der Überdeckung beider Profilbreiten zu dem self-Profil; bei 0.3 dürfen max 30% des self-Profilstreifens mit dem neuen Profil überlagert sein
    # Profilbreite: Breite zu einer Seite (also Gesamtbreite ist profilbreite*2)
    # bei return True sollte das Profil also nicht gemessen werden
    # lambda_intervall: bei None, soll das neue Profil unendlich lang sein, bei Angabe eben zwischen den beiden Lambdas liegen (als Liste, zB [-20,20] bei lamb 0 ist der Geradenpunkt gleich dem Stützpunkt)
    def PruefProfilExistiert(self, richtung, stuetzpunkt, profilbreite=5, toleranz=0.3, lambda_intervall=None):
        if not self.aktuelles_profil:
            test_profil_unendlich = not lambda_intervall # bestimmt, ob das neu zu rechnende Profil unendlich lang ist oder von Vornherein beschränkt ist
            self.lamb = 0
            fläche = (self.end_lambda-self.start_lambda) * 2 * profilbreite
            x = []
            y = []

            ### Clipping der neuen Profilfläche auf die alte ###
            # Berechnung der Eckpunkte des self-Profils
            eckpunkte = []
            for i in range(4):
                faktor = -1
                if i % 3 == 0:
                    faktor = 1
                punkt = self.BerechneNeuenKurspunkt(0, faktor * profilbreite)
                eckpunkte.append(punkt)
                if i == 1:
                    self.lamb = self.end_lambda

            # Berechnung der Eckpunkte und Richtungsvektoren des neu zu prüfenden Profils
            pruef_richtung = numpy.array([numpy.sin(richtung * numpy.pi / 200), numpy.cos(richtung * numpy.pi / 200)])
            pruef_stuetz = [] # Stützpunkte der beiden parallelen zunächst unendlich langen Geraden der Begrenzung des neu zu prüfenden Profils ODER die Eckpunkte des neuen Profils
            if test_profil_unendlich: # hier nur 2 "Eckpunkte" einführen
                temp_pruef_quer_richtung = numpy.array([richtung[1], -richtung[0]])
                pruef_stuetz.append(stuetzpunkt - profilbreite * temp_pruef_quer_richtung)
                pruef_stuetz.append(stuetzpunkt + profilbreite * temp_pruef_quer_richtung)
            else: # hier werden alle Eckpunkte eingeführt
                for i in range(4):
                    if i % 3 == 0:
                        pruef_lambda = lambda_intervall[0]
                    else:
                        pruef_lambda = lambda_intervall[1]
                    faktor = 1
                    if i <= 1:
                        faktor = -1
                    quer_richtung = numpy.array([pruef_richtung[1], -pruef_richtung[0]])
                    punkt = stuetzpunkt + (pruef_lambda) * pruef_richtung + (profilbreite * quer_richtung * faktor)
                    pruef_stuetz.append(punkt)

            def pruef_eckpunkt_in_neuem_profil(eckpunkt):
                pass

            # Schleife über alle Eckpunkte des self Profils
            test_richtung = numpy.array([-self.richtung[1], self.richtung[0]]) # Richtung der aktuell betrachteten Kante des self Profils
            for i, eckpunkt in enumerate(eckpunkte):
                # Test, ob Eckpunkt innerhalb des neuen Profils liegt und falls ja, hinzufügen
                if
                abst_g1 = abstand_punkt_gerade(pruef_richtung, pruef_stuetz[0], eckpunkt)
                abst_g2 = abstand_punkt_gerade(pruef_richtung, pruef_stuetz[1], eckpunkt)
                if (abst_g1 < 0 and abst_g2 > 0) or (abst_g1 > 0 and abst_g2 < 0):
                    x.append(eckpunkt[0])
                    y.append(eckpunkt[1])

                # Schnittpunktberechnung mit Kanten des neuen Profils
                #TODO: erst für alle Eckpunkte des self Punkte berechnen, dann alle Punkte mit dem neuen abchecken, ob die zuvor gefundenen Punkte auch in oder auf der Grenze des neuen liegen UND gucken, ob die Eckpunkte des neuen in dem self liege, falls nicht diese auch übernehmen (siehe Bild auf Cloud)
                p1 = schneide_geraden(test_richtung, eckpunkt, pruef_richtung, pruef_stuetz[0])
                p2 = schneide_geraden(test_richtung, eckpunkt, pruef_richtung, pruef_stuetz[1])
                if p1 is None and p2 is None: # wenn es keine oder nur sehr schleifende Schnittpunkte gibt, muss anders getestet werden
                    abst_g1 = abstand_punkt_gerade(test_richtung, eckpunkt, pruef_stuetz[0])# Abstand des Stützvektors der Geraden 1 des zu testenden Profils
                    abst_g2 = abstand_punkt_gerade(test_richtung, eckpunkt, pruef_stuetz[1])
                    if (abst_g1 < 0 and abst_g2 > 0) or (abst_g1 > 0 and abst_g2 < 0):
                        p1 = eckpunkt
                        p2 = eckpunkte[(i+1)%4]
                if p1 is not None and p2 is not None:
                    abst_stuetz_p1 = numpy.linalg.norm(p1 - eckpunkt)
                    abst_stuetz_p2 = numpy.linalg.norm(p2 - eckpunkt)
                    if abst_stuetz_p1 <= abst_stuetz_p2:
                        x.append(p1[0])
                        x.append(p2[0])
                        y.append(p1[1])
                        y.append(p2[1])
                    else:
                        x.append(p2[0])
                        x.append(p1[0])
                        y.append(p2[1])
                        y.append(p1[1])
                test_richtung = numpy.array([test_richtung[1], -test_richtung[0]])
                if not test_profil_unendlich:#TODO: muss in die Schleife über alle Punkte des neuen Profils (existiert noch nicht)
                    pruef_richtung = numpy.array([pruef_richtung[1], -pruef_richtung[0]])

            """
            # TODO: kann vllt entfallem entfernen der Schnittpunkte, die außerhalb des Profils liegen
            for eckpunkt in eckpunkte:
                for i in range(len(x) - 1, -1, -1):
                    test_punkt = numpy.array([x[i], y[i]])
                    abstand= abstand_punkt_gerade(test_richtung, eckpunkt, test_punkt)
                    if abstand < -0.001:
                        x.pop(i)
                        y.pop(i)
                test_richtung = numpy.array([test_richtung[1], -test_richtung[0]])
                """
            if len(x) >= 3:
                überdeckung = Flächenberechnung(numpy.array(x), numpy.array(y))
                return (überdeckung / fläche) > toleranz
            else:
                return False
        else:
            raise Exception

    def ProfilAbschliessen(self):
        self.aktuelles_profil = False
        self.end_lambda = self.lamb

# richtung und stuetz sind jeweils die 2D Vektoren der Geraden, und punkt der zu testende Punkt
def abstand_punkt_gerade(richtung, stuetz, punkt):
    richtung = numpy.array([richtung[1], -richtung[0]])
    return numpy.dot(richtung, (punkt - stuetz))

# Überprüfung, dass sich die Geraden schneiden, muss außerhalb der Funktion getestet werden!
def schneide_geraden(richtung1, stuetz1, richtung2, stuetz2, lamb_intervall_1=None, lamb_intervall_2=None):
    det = -1 * (richtung1[0]*richtung2[1]-richtung2[0]*richtung1[1])
    if abs(det) < 0.0000001: # falls kein oder sehr schleifender Schnitt existiert
        return None
    inverse = numpy.matrix([[-richtung2[1], richtung2[0]], [-richtung1[1], richtung1[0]]]) / det
    diff_stuetz = stuetz2 - stuetz1
    lambdas = numpy.array(inverse.dot(diff_stuetz))[0]
    if lamb_intervall_1 is not None and lamb_intervall_2 is not None:
        if not ((lamb_intervall_1[0] <= lambdas[0] <= lamb_intervall_1[1]) and (lamb_intervall_2[0] <= lambdas[1] <= lamb_intervall_2[1])):
            return None
    elif lamb_intervall_1 is not None:
        if not (lamb_intervall_1[0] <= lambdas[0] <= lamb_intervall_1[1]):
            return None
    punkt = stuetz1 + lambdas[0] * richtung1
    return punkt


# Klasse, die Daten der Messung temporär speichert
class Messgebiet:

    def __init__(self, initale_position, initiale_ausdehnung, auflösung):
        """
        :param initale_position: Mittige Position des zu vermessenden Gebiets (in utm), um das sich der Quadtree legen soll
        :param initiale_ausdehnung: grobe Ausdehnung in Meter
        :param auflösung:
        """
        self.quadtree = None
        self.uferlinie = None

    def daten_einspeisen(self, punkt, datenpaket):
        pass

    def daten_abfrage(self, punkt):
        pass

    def Zellenraster_erzeugen(self):
        self.zellenraster = False

    def Punkt_abspeichern(self):
        #Punkt zu einer Zelle zuordnen und in zelle abspeichern
        pass

if __name__=="__main__":

    richtung = 50
    stuetz = numpy.array([0,0])

    test_richtung = numpy.array([0,1])
    test_stuetz = numpy.array([10,0])

    profil = Profil(richtung, stuetz)
    profil.end_lambda = 20
    profil.lamb = 20
    profil.aktuelles_profil = False

    quer_richtung = numpy.array([profil.richtung[1], -profil.richtung[0]])
    punkt = profil.stuetzpunkt + (profil.lamb + 0) * profil.richtung + 5 * quer_richtung

    #print(profil.PruefProfilExistiert(test_richtung, test_stuetz))

    # Test Geradenschnitt
    richtung1 = numpy.array([1,1])
    richtung1 = richtung1 / numpy.linalg.norm(richtung1)
    richtung2 = numpy.array([0,1])
    stuetz1 = numpy.array([0,0])
    stuetz2 = numpy.array([5,0])
    print("========")
    print(schneide_geraden(richtung1, stuetz1, richtung2, stuetz2, [0,5], [0,10]))
