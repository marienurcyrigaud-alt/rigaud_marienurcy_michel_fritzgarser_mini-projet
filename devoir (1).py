import json
import os
from datetime import datetime, timedelta


class Billet:
    def __init__(self, id_billet, zone, prix):
        self.id_billet = id_billet
        self.zone = zone
        self.prix = prix
        self.annule = False
        self.utilise = False

    def to_dict(self):
        return {
            "id_billet": self.id_billet,
            "type": self.__class__.__name__,
            "zone": self.zone,
            "prix": self.prix,
            "annule": self.annule,
            "utilise": self.utilise
        }


class BilletStandard(Billet):
    def __init__(self, id_billet, zone, prix):
        super().__init__(id_billet, zone, prix)


class BilletVIP(Billet):
    def __init__(self, id_billet, zone, prix):
        super().__init__(id_billet, zone, prix)


class Evenement:
    def __init__(self, nom, date_evenement, zones_capacites, prix_standard, prix_vip, delai_remboursement=7):
        self.nom = nom
        self.date_evenement = date_evenement
        self.zones_capacites = zones_capacites
        self.prix_standard = prix_standard
        self.prix_vip = prix_vip
        self.delai_remboursement = delai_remboursement

        self.billets = []
        self.compteur_id = 0
        self.historique = []
        self.entrees = 0
        self.recettes_brutes = 0.0
        self.remboursements = 0.0

    def ajouter_historique(self, message):
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.historique.append(f"[{date_str}] {message}")

    def _places_disponibles(self):
        dispo = self.zones_capacites.copy()
        for b in self.billets:
            if not b.annule:
                dispo[b.zone] -= 1
        return dispo

    def reserver(self, demandes):
        dispo = self._places_disponibles()
        compte = {}

        for type_b, zone in demandes:
            if zone not in self.zones_capacites:
                raise ValueError(f"La zone '{zone}' n'existe pas.")
            compte[zone] = compte.get(zone, 0) + 1
            if compte[zone] > dispo[zone]:
                raise ValueError(f"Refusé : Plus assez de places en {zone}.")

        nouveaux_billets = []
        for type_b, zone in demandes:
            self.compteur_id += 1
            id_b = f"BIL-{self.compteur_id:04d}"

            if type_b == 'vip':
                b = BilletVIP(id_b, zone, self.prix_vip)
                prix = self.prix_vip
            else:
                b = BilletStandard(id_b, zone, self.prix_standard)
                prix = self.prix_standard

            self.billets.append(b)
            nouveaux_billets.append(b)
            self.recettes_brutes += prix

        self.ajouter_historique(f"Réservation de {len(demandes)} billet(s) réussie.")
        return nouveaux_billets

    def trouver_billet(self, id_b):
        for b in self.billets:
            if b.id_billet == id_b:
                return b
        return None

    def annuler_billet(self, id_b):
        b = self.trouver_billet(id_b)
        if not b:
            raise ValueError("Billet introuvable.")
        if b.annule or b.utilise:
            raise ValueError("Billet déjà annulé ou utilisé.")

        temps_restant = self.date_evenement - datetime.now()
        if temps_restant < timedelta(days=self.delai_remboursement):
            raise ValueError("Hors délai de remboursement.")

        b.annule = True
        self.remboursements += b.prix
        self.ajouter_historique(f"Annulation du billet {id_b}. Remboursement : {b.prix} GDS.")
        return True

    def controler_entree(self, id_b):
        b = self.trouver_billet(id_b)
        if not b:
            raise ValueError("Billet introuvable.")
        if b.annule:
            raise ValueError("Billet annulé.")
        if b.utilise:
            raise ValueError("Billet déjà utilisé.")

        b.utilise = True
        self.entrees += 1
        self.ajouter_historique(f"Entrée validée pour le billet {id_b}.")
        return True

    def to_dict(self):
        return {
            "nom": self.nom,
            "date_evenement": self.date_evenement.isoformat(),
            "zones_capacites": self.zones_capacites,
            "prix_standard": self.prix_standard,
            "prix_vip": self.prix_vip,
            "delai_remboursement": self.delai_remboursement,
            "compteur_id": self.compteur_id,
            "entrees": self.entrees,
            "recettes_brutes": self.recettes_brutes,
            "remboursements": self.remboursements,
            "historique": self.historique,
            "billets": [b.to_dict() for b in self.billets]
        }

    @classmethod
    def from_dict(cls, data):
        ev = cls(
            data["nom"],
            datetime.fromisoformat(data["date_evenement"]),
            data["zones_capacites"],
            data["prix_standard"],
            data["prix_vip"],
            data["delai_remboursement"]
        )
        ev.compteur_id = data["compteur_id"]
        ev.entrees = data["entrees"]
        ev.recettes_brutes = data["recettes_brutes"]
        ev.remboursements = data["remboursements"]
        ev.historique = data["historique"]

        for b_data in data["billets"]:
            if b_data["type"] == "BilletVIP":
                b = BilletVIP(b_data["id_billet"], b_data["zone"], b_data["prix"])
            else:
                b = BilletStandard(b_data["id_billet"], b_data["zone"], b_data["prix"])
            b.annule = b_data["annule"]
            b.utilise = b_data["utilise"]
            ev.billets.append(b)

        return ev


class Application:
    # J'AI CHANGÉ LE NOM DU FICHIER ICI
    def __init__(self, fichier_json="sauvegarde_cafe.json"):
        self.fichier = fichier_json
        self.evenement = None
        self.charger_donnees()

    def charger_donnees(self):
        if not os.path.exists(self.fichier):
            print("Création d'un nouvel événement par défaut.")
            self.evenement = Evenement(
                "Café Culturel", datetime.now() + timedelta(days=10),
                {'Terrain': 50, 'Balcon': 20}, 500.0, 1200.0
            )
            self.sauvegarder()
            return

        try:
            with open(self.fichier, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.evenement = Evenement.from_dict(data)
                print("Données chargées avec succès.")
        except Exception as e:
            print(f"Erreur de lecture du fichier JSON ({e}). Lancement d'un événement vierge.")
            self.evenement = Evenement(
                "Café Culturel", datetime.now() + timedelta(days=10),
                {'Terrain': 50, 'Balcon': 20}, 500.0, 1200.0
            )
            self.sauvegarder()

    def sauvegarder(self):
        with open(self.fichier, 'w', encoding='utf-8') as f:
            json.dump(self.evenement.to_dict(), f, indent=4, ensure_ascii=False)

    def menu(self):
        while True:
            print("\n" + "=" * 40)
            print(f" BILLETTERIE : {self.evenement.nom}")
            print("=" * 40)
            print("1. Réserver des billets")
            print("2. Valider une entrée")
            print("3. Annuler un billet")
            print("4. Afficher le bilan et l'historique")
            print("5. Quitter")

            choix = input("Votre choix : ")

            try:
                if choix == '1':
                    self.menu_reservation()
                elif choix == '2':
                    id_b = input("Entrez l'ID du billet : ")
                    self.evenement.controler_entree(id_b)
                    print("Entrée validée !")
                    self.sauvegarder()
                elif choix == '3':
                    id_b = input("Entrez l'ID du billet : ")
                    self.evenement.annuler_billet(id_b)
                    print("Billet annulé et remboursé !")
                    self.sauvegarder()
                elif choix == '4':
                    self.afficher_bilan()
                elif choix == '5':
                    print("Sauvegarde et fermeture...")
                    self.sauvegarder()
                    break
                else:
                    print("Choix invalide.")
            except ValueError as e:
                print(f"ERREUR : {e}")

    def menu_reservation(self):
        dispo = self.evenement._places_disponibles()
        texte_dispo = " | ".join([f"{zone}: {places}" for zone, places in dispo.items()])
        print(f"Places dispo : {texte_dispo}")

        demandes = []
        while True:
            zone = input("Zone (Terrain/Balcon) ou 'stop' pour terminer : ").capitalize()
            if zone.lower() == 'stop': break
            type_b = input("Type (standard/vip) : ").lower()
            demandes.append((type_b, zone))

        if demandes:
            nouveaux = self.evenement.reserver(demandes)
            print(f"Succès ! Billets créés : {[b.id_billet for b in nouveaux]}")
            self.sauvegarder()

    def afficher_bilan(self):
        ev = self.evenement
        actifs = sum(1 for b in ev.billets if not b.annule)
        net = ev.recettes_brutes - ev.remboursements

        dispo = ev._places_disponibles()
        texte_dispo = " | ".join([f"{zone}: {places}" for zone, places in dispo.items()])

        print(f"\n--- BILAN {ev.nom} ---")
        print(f"Dispo : {texte_dispo}")
        print(f"Billets vendus (actifs) : {actifs}")
        print(f"Entrées validées : {ev.entrees}")
        print(f"Recettes brutes : {ev.recettes_brutes} GDS | Remboursements : {ev.remboursements} GDS")
        print(f"Recettes nettes : {net} GDS")
        print("\n--- HISTORIQUE (5 dernières actions) ---")
        for log in ev.historique[-5:]:
            print(log)


if __name__ == "__main__":
    app = Application()
    app.menu()
    