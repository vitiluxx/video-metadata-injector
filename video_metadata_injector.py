#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
    OPTIMIZED VIDEO METADATA INJECTOR - VERSION 2.0 PRODUCTION
    
    Programme haute performance pour l'injection de métadonnées dans vidéos
    Utilise FFmpeg + optimisations multi-threading + traitement par lots
═══════════════════════════════════════════════════════════════════════════════

ARCHITECTURE:
    - Python 3.8+ (orchestration et interface)
    - FFmpeg (moteur vidéo C/C++ optimisé)
    - Multi-threading (traitement parallèle)
    - Traitement par lots (batch processing)
    
AUTEUR: Système d'injection de métadonnées optimisé
VERSION: 2.0 Production-Ready
DATE: 2026-01-22
"""

import subprocess
import sys
import os
import json
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION GLOBALE
# ═══════════════════════════════════════════════════════════════════════════

VERSION = "2.0.0"
MAX_WORKERS = os.cpu_count() or 4  # Threads parallèles = nombre de CPU
BUFFER_SIZE = 8192  # Buffer I/O optimisé
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION DU LOGGING
# ═══════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('video_metadata.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CLASSES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VideoProcessingResult:
    """Résultat du traitement d'une vidéo"""
    input_file: str
    output_file: str
    success: bool
    duration: float
    error_message: Optional[str] = None
    file_size_before: int = 0
    file_size_after: int = 0


@dataclass
class ProcessingStats:
    """Statistiques globales de traitement"""
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    total_duration: float = 0.0
    total_size_before: int = 0
    total_size_after: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE - VIDEO METADATA PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════

class OptimizedVideoMetadataProcessor:
    """
    Processeur haute performance pour l'injection de métadonnées vidéo
    
    OPTIMISATIONS:
        - Multi-threading pour traitement parallèle
        - Mode copy FFmpeg (pas de réencodage = 100x plus rapide)
        - Traitement par lots
        - Gestion mémoire optimisée
        - Logging détaillé pour monitoring
    """
    
    def __init__(self, max_workers: int = MAX_WORKERS, verbose: bool = True):
        """
        Initialisation du processeur
        
        Args:
            max_workers: Nombre de threads parallèles (défaut: nombre de CPU)
            verbose: Mode verbeux pour logs détaillés
        """
        self.max_workers = max_workers
        self.verbose = verbose
        self.stats = ProcessingStats()
        
        logger.info(f"╔{'═' * 78}╗")
        logger.info(f"║ OPTIMIZED VIDEO METADATA PROCESSOR v{VERSION:^42} ║")
        logger.info(f"║ {'Configuration:':^76} ║")
        logger.info(f"║   • Threads parallèles: {max_workers:<54} ║")
        logger.info(f"║   • CPU disponibles: {os.cpu_count():<57} ║")
        logger.info(f"║   • Mode: Production                                                    ║")
        logger.info(f"╚{'═' * 78}╝")
        
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> None:
        """
        Vérifie la disponibilité de FFmpeg et ses capacités
        
        FFmpeg est écrit en C/C++ avec optimisations assembleur pour:
            - Décodage vidéo hardware-accelerated
            - SIMD (SSE, AVX) pour traitement parallèle
            - Multi-threading natif
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )
            
            version_line = result.stdout.split('\n')[0]
            logger.info(f"✓ FFmpeg détecté: {version_line}")
            
            # Vérification des capacités hardware
            if 'configuration:' in result.stdout:
                if '--enable-cuda' in result.stdout:
                    logger.info("✓ Accélération GPU CUDA disponible")
                if '--enable-opencl' in result.stdout:
                    logger.info("✓ Accélération OpenCL disponible")
                    
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("✗ FFmpeg non trouvé!")
            logger.error("Installation requise:")
            logger.error("  • Windows: https://ffmpeg.org/download.html")
            logger.error("  • macOS:   brew install ffmpeg")
            logger.error("  • Linux:   sudo apt install ffmpeg")
            sys.exit(1)
    
    def _get_file_hash(self, filepath: str) -> str:
        """Calcule le hash SHA256 d'un fichier pour vérification d'intégrité"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(BUFFER_SIZE):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _process_single_video(
        self,
        input_file: str,
        output_file: str,
        metadata: Dict[str, str]
    ) -> VideoProcessingResult:
        """
        Traite une seule vidéo (fonction thread-safe pour parallélisation)
        
        OPTIMISATIONS FFmpeg utilisées:
            -c copy          : Copie directe des streams (pas de réencodage)
            -map_metadata 0  : Préserve les métadonnées existantes
            -threads 0       : Utilise tous les CPU disponibles
            -y               : Écrase sans confirmation
        
        Args:
            input_file: Chemin du fichier source
            output_file: Chemin du fichier destination
            metadata: Dictionnaire des métadonnées à injecter
            
        Returns:
            VideoProcessingResult avec statistiques
        """
        start_time = time.time()
        
        try:
            # Vérifications préliminaires
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Fichier introuvable: {input_file}")
            
            file_size_before = os.path.getsize(input_file)
            
            # Construction de la commande FFmpeg optimisée
            cmd = [
                'ffmpeg',
                '-i', input_file,           # Input
                '-map_metadata', '0',       # Préserve métadonnées existantes
                '-c', 'copy',               # Mode copie (pas de réencodage)
                '-threads', '0',            # Multi-threading auto
            ]
            
            # Injection des métadonnées personnalisées
            for key, value in metadata.items():
                # Échappement des caractères spéciaux pour la ligne de commande
                safe_value = value.replace('"', '\\"').replace('\n', '\\n')
                cmd.extend(['-metadata', f'{key}={safe_value}'])
            
            cmd.extend([
                '-y',                       # Écrasement automatique
                output_file
            ])
            
            # Exécution avec capture des erreurs
            if self.verbose:
                logger.debug(f"Commande FFmpeg: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # Vérification post-traitement
            if not os.path.exists(output_file):
                raise RuntimeError("Fichier de sortie non créé")
            
            file_size_after = os.path.getsize(output_file)
            duration = time.time() - start_time
            
            logger.info(f"✓ Traité: {os.path.basename(input_file)} "
                       f"({file_size_before / 1024 / 1024:.2f} MB) "
                       f"en {duration:.2f}s")
            
            return VideoProcessingResult(
                input_file=input_file,
                output_file=output_file,
                success=True,
                duration=duration,
                file_size_before=file_size_before,
                file_size_after=file_size_after
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"✗ Échec: {os.path.basename(input_file)} - {error_msg}")
            
            return VideoProcessingResult(
                input_file=input_file,
                output_file=output_file,
                success=False,
                duration=duration,
                error_message=error_msg
            )
    
    def process_batch(
        self,
        video_files: List[str],
        metadata: Dict[str, str],
        output_dir: Optional[str] = None,
        suffix: str = "_metadata"
    ) -> List[VideoProcessingResult]:
        """
        Traite un lot de vidéos en parallèle
        
        OPTIMISATION: Utilise ThreadPoolExecutor pour traitement multi-thread
        Chaque vidéo est traitée dans un thread séparé, maximisant l'utilisation CPU
        
        Args:
            video_files: Liste des chemins des vidéos à traiter
            metadata: Métadonnées à injecter dans toutes les vidéos
            output_dir: Répertoire de sortie (défaut: même que source)
            suffix: Suffixe ajouté aux noms de fichiers
            
        Returns:
            Liste des résultats de traitement
        """
        logger.info(f"\n{'═' * 80}")
        logger.info(f"TRAITEMENT PAR LOTS")
        logger.info(f"{'═' * 80}")
        logger.info(f"Fichiers à traiter: {len(video_files)}")
        logger.info(f"Threads parallèles: {self.max_workers}")
        logger.info(f"Métadonnées: {len(metadata)} champs")
        logger.info(f"{'═' * 80}\n")
        
        results = []
        
        # Préparation des tâches
        tasks = []
        for input_file in video_files:
            input_path = Path(input_file)
            
            if output_dir:
                output_path = Path(output_dir) / f"{input_path.stem}{suffix}{input_path.suffix}"
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = input_path.parent / f"{input_path.stem}{suffix}{input_path.suffix}"
            
            tasks.append((input_file, str(output_path), metadata))
        
        # Exécution parallèle avec ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumission de toutes les tâches
            future_to_task = {
                executor.submit(self._process_single_video, *task): task
                for task in tasks
            }
            
            # Collecte des résultats au fur et à mesure
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
                
                # Mise à jour des statistiques
                self.stats.total_files += 1
                if result.success:
                    self.stats.successful += 1
                    self.stats.total_size_before += result.file_size_before
                    self.stats.total_size_after += result.file_size_after
                else:
                    self.stats.failed += 1
                self.stats.total_duration += result.duration
        
        return results
    
    def read_metadata(self, video_file: str) -> Dict[str, str]:
        """
        Lit les métadonnées existantes d'une vidéo
        
        Utilise ffprobe (outil C de la suite FFmpeg) pour extraction rapide
        
        Args:
            video_file: Chemin du fichier vidéo
            
        Returns:
            Dictionnaire des métadonnées
        """
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_file
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            
            if 'format' in data and 'tags' in data['format']:
                return data['format']['tags']
            return {}
            
        except Exception as e:
            logger.error(f"Erreur lecture métadonnées: {e}")
            return {}
    
    def print_statistics(self) -> None:
        """Affiche les statistiques de traitement"""
        logger.info(f"\n{'═' * 80}")
        logger.info(f"STATISTIQUES FINALES")
        logger.info(f"{'═' * 80}")
        logger.info(f"Total fichiers traités:  {self.stats.total_files}")
        logger.info(f"  ✓ Succès:              {self.stats.successful}")
        logger.info(f"  ✗ Échecs:              {self.stats.failed}")
        
        if self.stats.successful > 0:
            logger.info(f"Taille totale avant:     {self.stats.total_size_before / 1024 / 1024:.2f} MB")
            logger.info(f"Taille totale après:     {self.stats.total_size_after / 1024 / 1024:.2f} MB")
            logger.info(f"Temps total:             {self.stats.total_duration:.2f}s")
            logger.info(f"Temps moyen/vidéo:       {self.stats.total_duration / self.stats.successful:.2f}s")
            
            # Calcul du débit de traitement
            throughput_mb_s = (self.stats.total_size_before / 1024 / 1024) / self.stats.total_duration
            logger.info(f"Débit de traitement:     {throughput_mb_s:.2f} MB/s")
        
        logger.info(f"{'═' * 80}\n")


# ═══════════════════════════════════════════════════════════════════════════
# MODE INTERACTIF
# ═══════════════════════════════════════════════════════════════════════════

def interactive_mode():
    """Mode interactif avec interface utilisateur guidée"""
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║            OPTIMIZED VIDEO METADATA INJECTOR v{VERSION}                          ║
║            Mode Interactif - Production Ready                                 ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
    
    processor = OptimizedVideoMetadataProcessor()
    
    # Collecte des fichiers
    print("\n📁 FICHIERS À TRAITER")
    print("─" * 80)
    print("Options:")
    print("  1. Un seul fichier")
    print("  2. Plusieurs fichiers (séparés par des virgules)")
    print("  3. Tous les fichiers d'un dossier")
    
    choice = input("\nVotre choix (1/2/3): ").strip()
    
    video_files = []
    
    if choice == "1":
        file_path = input("Chemin du fichier: ").strip()
        if os.path.exists(file_path):
            video_files.append(file_path)
        else:
            print(f"✗ Fichier introuvable: {file_path}")
            return
            
    elif choice == "2":
        files_input = input("Chemins des fichiers (séparés par des virgules): ").strip()
        for file_path in files_input.split(','):
            file_path = file_path.strip()
            if os.path.exists(file_path):
                video_files.append(file_path)
            else:
                print(f"⚠ Fichier ignoré (introuvable): {file_path}")
                
    elif choice == "3":
        folder = input("Chemin du dossier: ").strip()
        if os.path.isdir(folder):
            extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
            for file in os.listdir(folder):
                if Path(file).suffix.lower() in extensions:
                    video_files.append(os.path.join(folder, file))
            print(f"✓ {len(video_files)} fichiers vidéo trouvés")
        else:
            print(f"✗ Dossier introuvable: {folder}")
            return
    else:
        print("✗ Choix invalide")
        return
    
    if not video_files:
        print("✗ Aucun fichier à traiter")
        return
    
    # Collecte des métadonnées
    print(f"\n📝 MÉTADONNÉES À INJECTER")
    print("─" * 80)
    print("Entrez vos métadonnées personnalisées (laissez vide pour terminer)")
    print()
    
    metadata = {}
    
    # Suggestions de champs
    suggestions = [
        ('title', 'Titre'),
        ('artist', 'Créateur/Artiste'),
        ('description', 'Description'),
        ('tags', 'Tags (séparés par virgules)'),
        ('hashtags', 'Hashtags (ex: #video #tutorial)'),
        ('category', 'Catégorie'),
        ('project', 'Nom du projet'),
        ('comment', 'Commentaire'),
        ('copyright', 'Copyright'),
        ('date', 'Date (YYYY-MM-DD)'),
    ]
    
    for key, label in suggestions:
        value = input(f"  {label}: ").strip()
        if value:
            metadata[key] = value
    
    # Métadonnées personnalisées
    print("\n💡 Champs personnalisés supplémentaires:")
    while True:
        key = input("  Nom du champ (vide pour terminer): ").strip()
        if not key:
            break
        value = input(f"  Valeur de '{key}': ").strip()
        if value:
            metadata[key] = value
    
    if not metadata:
        print("⚠ Aucune métadonnée saisie. Abandon.")
        return
    
    # Affichage récapitulatif
    print(f"\n{'═' * 80}")
    print("RÉCAPITULATIF")
    print(f"{'═' * 80}")
    print(f"Fichiers à traiter: {len(video_files)}")
    print(f"Métadonnées:")
    for key, value in metadata.items():
        print(f"  • {key}: {value}")
    print(f"{'═' * 80}")
    
    # Confirmation
    confirm = input("\n▶ Lancer le traitement? (o/n): ").lower()
    if confirm != 'o':
        print("✗ Opération annulée")
        return
    
    # Traitement
    print()
    results = processor.process_batch(video_files, metadata)
    
    # Affichage des résultats
    processor.print_statistics()
    
    print("\n📋 DÉTAILS DES RÉSULTATS:")
    print("─" * 80)
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"{status} {os.path.basename(result.input_file)}")
        if result.success:
            print(f"   → {result.output_file}")
            print(f"   Durée: {result.duration:.2f}s")
        else:
            print(f"   Erreur: {result.error_message}")
    print("─" * 80)


# ═══════════════════════════════════════════════════════════════════════════
# MODE LIGNE DE COMMANDE (CLI)
# ═══════════════════════════════════════════════════════════════════════════

def cli_mode():
    """Mode ligne de commande pour scripts et automatisation"""
    parser = argparse.ArgumentParser(
        description='Optimized Video Metadata Injector v' + VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLES D'UTILISATION:

  # Un seul fichier avec métadonnées
  python video_metadata.py -i video.mp4 -m title="Ma vidéo" artist="John Doe"
  
  # Plusieurs fichiers en parallèle
  python video_metadata.py -i video1.mp4 video2.mp4 video3.mp4 -m title="Titre" tags="test,demo"
  
  # Tous les fichiers d'un dossier
  python video_metadata.py -d ./videos/ -m project="Mon Projet" category="Tutorial"
  
  # Avec sortie dans dossier spécifique
  python video_metadata.py -i video.mp4 -o ./output/ -m title="Test"
  
  # Lecture de métadonnées existantes
  python video_metadata.py --read video.mp4
        """
    )
    
    parser.add_argument('-i', '--input', nargs='+', help='Fichier(s) vidéo à traiter')
    parser.add_argument('-d', '--directory', help='Dossier contenant les vidéos')
    parser.add_argument('-o', '--output', help='Dossier de sortie')
    parser.add_argument('-m', '--metadata', nargs='+', help='Métadonnées (format: key=value)')
    parser.add_argument('-s', '--suffix', default='_metadata', help='Suffixe pour fichiers de sortie')
    parser.add_argument('-t', '--threads', type=int, default=MAX_WORKERS, help='Nombre de threads parallèles')
    parser.add_argument('--read', help='Lire les métadonnées d\'un fichier')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    
    args = parser.parse_args()
    
    # Mode lecture de métadonnées
    if args.read:
        processor = OptimizedVideoMetadataProcessor(verbose=args.verbose)
        metadata = processor.read_metadata(args.read)
        
        print(f"\n{'═' * 80}")
        print(f"MÉTADONNÉES DE: {args.read}")
        print(f"{'═' * 80}")
        
        if metadata:
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        else:
            print("  Aucune métadonnée trouvée")
        
        print(f"{'═' * 80}\n")
        return
    
    # Collecte des fichiers
    video_files = []
    
    if args.input:
        video_files.extend(args.input)
    
    if args.directory:
        if not os.path.isdir(args.directory):
            logger.error(f"Dossier introuvable: {args.directory}")
            sys.exit(1)
        
        extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        for file in os.listdir(args.directory):
            if Path(file).suffix.lower() in extensions:
                video_files.append(os.path.join(args.directory, file))
    
    if not video_files:
        logger.error("Aucun fichier vidéo spécifié. Utilisez -i ou -d")
        parser.print_help()
        sys.exit(1)
    
    # Parse des métadonnées
    metadata = {}
    if args.metadata:
        for item in args.metadata:
            if '=' in item:
                key, value = item.split('=', 1)
                metadata[key.strip()] = value.strip()
    
    if not metadata:
        logger.error("Aucune métadonnée spécifiée. Utilisez -m")
        parser.print_help()
        sys.exit(1)
    
    # Traitement
    processor = OptimizedVideoMetadataProcessor(
        max_workers=args.threads,
        verbose=args.verbose
    )
    
    results = processor.process_batch(
        video_files,
        metadata,
        output_dir=args.output,
        suffix=args.suffix
    )
    
    processor.print_statistics()
    
    # Code de sortie basé sur les résultats
    sys.exit(0 if processor.stats.failed == 0 else 1)


# ═══════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Point d'entrée principal - détecte le mode d'exécution"""
    try:
        # Si arguments CLI fournis, utiliser mode CLI
        if len(sys.argv) > 1:
            cli_mode()
        else:
            # Sinon, mode interactif
            interactive_mode()
            
    except KeyboardInterrupt:
        print("\n\n⚠ Opération annulée par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
