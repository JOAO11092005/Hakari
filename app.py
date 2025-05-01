import subprocess
import sys

# Verificação e instalação de dependências
REQUIRED_PACKAGES = ["m3u8", "requests", "tqdm", "boto3", "botocore"]

def install_missing_packages():
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            print(f"[🔧] Instalando pacote: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])

install_missing_packages()

# Imports após instalação
import os
import requests
import m3u8
import concurrent.futures
from urllib.parse import urljoin
from tqdm import tqdm
import boto3
from botocore.client import Config

# 📂 Configurações
TEMP_FOLDER = "temp_segments"
BUCKET_NAME = "devquest"
R2_ENDPOINT = "https://49d20e4dc15e78e73d71dbb668ba5767.r2.cloudflarestorage.com"
R2_PUBLIC_URL = "https://pub-805753a22e7e4f2dac776cf9d9ed2bf3.r2.dev"

# 🔐 Credenciais (proteja isso em produção!)
ACCESS_KEY = "1d626f78033d1ef35db61d69c5742eb6"
SECRET_KEY = "9e6a99aed0fa76eb3223966b6e0e9d65ada18db2c784c9a2f4d48a618a945c3d"

def download_m3u8(url):
    print(f"[INFO] Baixando playlist .m3u8 de: {url}")
    r = requests.get(url)
    r.raise_for_status()
    return m3u8.loads(r.text), url

def download_segment(segment_url, segment_index):
    local_filename = os.path.join(TEMP_FOLDER, f"seg_{segment_index:05d}.ts")
    try:
        r = requests.get(segment_url, stream=True, timeout=15)
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return local_filename
    except Exception as e:
        print(f"[ERRO] Falha no segmento {segment_index}: {e}")
        return None

def merge_segments(segment_files, output_file):
    print(f"[INFO] Unindo {len(segment_files)} segmentos em {output_file}")
    with open(output_file, 'wb') as outfile:
        for file in segment_files:
            with open(file, 'rb') as seg:
                outfile.write(seg.read())

def clean_temp_files(segment_files):
    print(f"[INFO] Limpando arquivos temporários...")
    for file in segment_files:
        if os.path.exists(file):
            os.remove(file)
    if os.path.exists(TEMP_FOLDER):
        os.rmdir(TEMP_FOLDER)

def escolher_melhor_resolucao(playlist):
    resolucoes = [p for p in playlist.playlists if p.stream_info.resolution and p.stream_info.resolution[1] >= 720]
    resolucoes.sort(key=lambda x: x.stream_info.resolution[0] * x.stream_info.resolution[1], reverse=True)
    melhor = resolucoes[0]
    print(f"[AUTO] Selecionada resolução: {melhor.stream_info.resolution}")
    return melhor.uri

def upload_to_r2(file_path, object_name):
    print("[INFO] Enviando vídeo para Cloudflare R2...")

    session = boto3.session.Session()
    s3 = session.client('s3',
                        region_name='auto',
                        endpoint_url=R2_ENDPOINT,
                        aws_access_key_id=ACCESS_KEY,
                        aws_secret_access_key=SECRET_KEY,
                        config=Config(signature_version='s3v4'))

    file_size = os.path.getsize(file_path)
    progress = tqdm(total=file_size, unit='B', unit_scale=True, desc="Upload R2")

    def progress_callback(bytes_transferred):
        progress.update(bytes_transferred)

    try:
        with open(file_path, "rb") as f:
            s3.upload_fileobj(f, BUCKET_NAME, object_name, Callback=progress_callback)
        progress.close()
        public_url = f"{R2_PUBLIC_URL}/{object_name}"
        print(f"✅ Upload concluído: {public_url}")
        return public_url
    except Exception as e:
        print(f"[ERRO] Falha ao enviar para R2: {e}")
        return None

def delete_local_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"[INFO] Arquivo local removido: {file_path}")

def main():
    print("🎬 Panda Video Downloader + Upload Automático R2")
    m3u8_url = input("📥 Cole o link .m3u8: ").strip()
    output_name = input("📝 Nome do arquivo final (sem .mp4): ").strip() or "video_final"
    output_file = output_name + ".mp4"

    if ".m3u8" not in m3u8_url:
        print("[ERRO] Link inválido.")
        return

    os.makedirs(TEMP_FOLDER, exist_ok=True)
    playlist, base_url = download_m3u8(m3u8_url)

    if playlist.is_variant:
        variant_uri = escolher_melhor_resolucao(playlist)
        variant_url = urljoin(base_url, variant_uri)
        playlist, base_url = download_m3u8(variant_url)

    segment_urls = [urljoin(base_url, seg.uri) for seg in playlist.segments]
    print(f"[INFO] Total de segmentos: {len(segment_urls)}")

    segment_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(download_segment, url, idx) for idx, url in enumerate(segment_urls)]
        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Baixando"):
            result = f.result()
            if result:
                segment_files.append(result)

    segment_files.sort()
    merge_segments(segment_files, output_file)
    clean_temp_files(segment_files)

    video_url = upload_to_r2(output_file, os.path.basename(output_file))
    delete_local_file(output_file)

    print("\n✅ Finalizado com sucesso.")
    print(f"📺 Link público do vídeo: {video_url}")

if __name__ == "__main__":
    main()
