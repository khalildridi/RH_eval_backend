import pandas as pd
from typing import List, Dict, Any
import math
# 🌟 Importation de re pour le nettoyage des chaînes
import re 

# Mappage des colonnes attendues (flexible)
# La clé est le nom normalisé (attendu par Pydantic), 
# La valeur est une liste de noms possibles dans le fichier CSV/Excel
COLUMN_MAP = {
    # ───────────────────────────────────────────────────────────
    # Ajout des en-têtes descriptifs et des variantes
    # ───────────────────────────────────────────────────────────
    # Ajout de REF FFREF COMP, qui semble être le nom exact dans votre fichier
    "refComp": ["REF COMP", "REF", "REFERENCE", "refComp", "REF COMPÉTENCE", "REF FFREF COMP"],
    "domaine": ["DOMAINE", "domaine", "DOMAINE DE COMPETENCE", "DOMAINE DE COMPÉTENCE"],
    "axe": ["AXE", "axe", "AXE DE COMPETENCE", "AXE DE COMPÉTENCE"],
    "categorie": ["CATÉGORIE", "CATEGORIE", "categorie"],
    "nom": ["COMPETENCE", "NOM", "nom"],
    "definition": ["DEFINITION", "description", "definition"],
    # Mise à jour des Niveaux pour gérer les suffixes (ex: N1 – DÉBUTANT)
    "n1": ["N1", "NIVEAU 1", "N1 – DÉBUTANT", "N1 - DÉBUTANT", "N1 - DEBUTANT"], 
    "n2": ["N2", "NIVEAU 2", "N2 – INTERMÉDIAIRE", "N2 - INTERMÉDIAIRE", "N2 - INTERMEDIAIRE"],
    "n3": ["N3", "NIVEAU 3", "N3 – AVANCÉ", "N3 - AVANCÉ", "N3 - AVANCE"],
    "n4": ["N4", "NIVEAU 4", "N4 – EXPERT", "N4 - EXPERT"],
    "n5": ["N5", "NIVEAU 5"], 
    "niveauAttendu": ["NIVEAU ATTENDU", "NIVEAU REQUIS", "niveauAttendu", "NIVEAU ATTENDU"],
    "norme": ["NORME", "norme", "NORME SI APPLICABLE"],
}

# Colonnes requises pour qu'une ligne soit valide
REQUIRED_COLS = ["refComp", "nom", "domaine", "axe", "categorie"]

def clean_header_string(header: str) -> str:
    """Nettoie une chaîne d'en-tête pour la normalisation."""
    # Remplacer tout type d'espace (y compris \xa0 et espaces multiples) par un espace standard
    cleaned = re.sub(r'\s+', ' ', str(header).replace('\xa0', ' '))
    # Convertir en majuscule et enlever les espaces début/fin
    return cleaned.strip().upper()

def normalize_headers(headers: List[str]) -> Dict[str, str]:
    """Normalise les en-têtes de colonnes trouvés dans le fichier."""
    norm_map = {}
    
    # Prénormaliser tous les noms possibles du dictionnaire pour une comparaison efficace
    upper_possible_names_map = {}
    for norm_key, possible_names in COLUMN_MAP.items():
        for name in possible_names:
            upper_possible_names_map[clean_header_string(name)] = norm_key
            
    for header in headers:
        original_header_key = str(header)
        header_clean = clean_header_string(original_header_key)

        # Chercher la clé normalisée dans la map pré-calculée
        if header_clean in upper_possible_names_map:
            norm_map[original_header_key] = upper_possible_names_map[header_clean]
            
    return norm_map

def clean_value(value: Any) -> Any:
    """Nettoie les valeurs (ex: NaN de pandas)."""
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        return value.strip()
    return value

async def parse_referentiel_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse un fichier CSV ou XLSX et le transforme en liste de dicts."""
    try:
        # Tenter de lire le fichier
        if file_path.endswith('.csv'):
            # Essayer point-virgule puis virgule
            try:
                # Utilisation d'encoding utf-8 qui est souvent plus sûr
                df = pd.read_csv(file_path, sep=';', dtype=str, encoding='utf-8')
            except:
                df = pd.read_csv(file_path, sep=',', dtype=str, encoding='utf-8')
        elif file_path.endswith('.xlsx'):
            # 🌟 CORRECTION CLÉ: Lecture du fichier Excel en spécifiant que les en-têtes 
            # sont sur la deuxième ligne (index 1)
            df = pd.read_excel(file_path, dtype=str, header=1)
        else:
            raise ValueError("Format de fichier non supporté")
            
    except Exception as e:
        # Renvoyer une erreur générique pour le parsing de fichier
        raise ValueError(f"Impossible de lire le fichier: {e}")

    # Normaliser les en-têtes
    norm_map = normalize_headers(df.columns.tolist())
    
    # Remplacer les colonnes originales par les clés normalisées si elles existent
    df_normalized = pd.DataFrame()
    found_cols = set()
    for original_col in df.columns.tolist():
        if original_col in norm_map:
            normalized_key = norm_map[original_col]
            df_normalized[normalized_key] = df[original_col]
            found_cols.add(normalized_key)
        # Si une colonne n'est pas mappée, elle est ignorée dans df_normalized

    # Vérifier les colonnes requises dans le DataFrame normalisé
    missing_cols = [col for col in REQUIRED_COLS if col not in found_cols]
    if missing_cols:
        # AFFICHE LES EN-TÊTES TROUVÉS POUR DEBUG
        cleaned_headers_found = [clean_header_string(h) for h in df.columns.tolist()]
        raise ValueError(
            f"Colonnes requises manquantes après normalisation: {', '.join(missing_cols)}. "
            f"En-têtes nettoyés trouvés dans le fichier: {', '.join(cleaned_headers_found)}. "
        )

    parsed_data = []
    
    # Convertir en dicts
    for record in df_normalized.to_dict(orient='records'):
        cleaned_record = {k: clean_value(v) for k, v in record.items()}

        # Ignorer les lignes vides (basé sur la clé primaire)
        if not cleaned_record.get("refComp"):
            continue

        # Structurer les niveaux
        niveaux_data = {
            "n1": cleaned_record.get("n1"),
            "n2": cleaned_record.get("n2"),
            "n3": cleaned_record.get("n3"),
            "n4": cleaned_record.get("n4"),
            "n5": cleaned_record.get("n5"),
        }
        
        # Créer l'objet final
        competence_dict = {
            "refComp": cleaned_record.get("refComp"),
            "domaine": cleaned_record.get("domaine"),
            "axe": cleaned_record.get("axe"),
            "categorie": cleaned_record.get("categorie"),
            "nom": cleaned_record.get("nom"),
            "definition": cleaned_record.get("definition"),
            # Tenter de convertir le niveau attendu en int, si possible
            "niveauAttendu": int(cleaned_record.get("niveauAttendu").replace('N', '')) if cleaned_record.get("niveauAttendu") and str(cleaned_record.get("niveauAttendu")).upper().startswith('N') and str(cleaned_record.get("niveauAttendu"))[1:].isdigit() else cleaned_record.get("niveauAttendu"),
            "norme": cleaned_record.get("norme"),
            "niveaux": {k: v for k, v in niveaux_data.items() if v is not None} # Nettoyer les niveaux nuls
        }
        
        parsed_data.append(competence_dict)
        
    return parsed_data