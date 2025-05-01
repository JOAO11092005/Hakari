import os
import requests
import m3u8
import concurrent.futures
from urllib.parse import urljoin
from tqdm import tqdm

TEMP_FOLDER = "temp_segments"

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
    print("\n🎯 Resoluções disponíveis:")
    resolucoes = []

    for idx, p in enumerate(playlist.playlists):
        stream_info = p.stream_info
        res = stream_info.resolution
        bandwidth = stream_info.bandwidth or 0
        resolution = f"{res[0]}x{res[1]}" if res else "Desconhecida"
        print(f"[{idx}] {resolution} - {p.uri} (bitrate: {bandwidth})")
        resolucoes.append((res, bandwidth, p.uri))

    # Filtra resoluções menores que 720p e tenta pegar 4K ou Ultra HD
    resolucoes = [r for r in resolucoes if r[0] and r[0][1] >= 720]

    # Ordena por resolução (largura * altura), depois por largura se empatar
    resolucoes.sort(key=lambda x: (x[0][0] * x[0][1]) if x[0] else 0, reverse=True)

    melhor_resolucao_uri = resolucoes[0][2]
    print(f"\n⭐ Selecionando automaticamente a melhor resolução: {melhor_resolucao_uri}")
    return melhor_resolucao_uri

def main():
    print("Auditor de Segurança do Player Panda Video (sem ffmpeg)")
    m3u8_url = input("Cole o link direto do .m3u8: ").strip()
    output_name = input("Nome do arquivo final (sem extensão): ").strip() or "output"
    output_file = output_name + ".mp4"

    if ".m3u8" not in m3u8_url:
        print("[ERRO] Esse link não parece ser um .m3u8. Verifique no DevTools.")
        return

    os.makedirs(TEMP_FOLDER, exist_ok=True)
    playlist, base_url = download_m3u8(m3u8_url)

    if playlist.is_variant:
        print("[INFO] Playlist tem múltiplas resoluções.")
        variant_uri = escolher_melhor_resolucao(playlist)
        variant_url = urljoin(base_url, variant_uri)
        playlist, base_url = download_m3u8(variant_url)

    segment_urls = [urljoin(base_url, seg.uri) for seg in playlist.segments]

    print(f"[INFO] Total de segmentos: {len(segment_urls)}")
    segment_files = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for idx, url in enumerate(segment_urls):
            futures.append(executor.submit(download_segment, url, idx))

        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Baixando"):
            result = f.result()
            if result:
                segment_files.append(result)

    segment_files.sort()
    merge_segments(segment_files, output_file)
    clean_temp_files(segment_files)

    print(f"\n✅ Download finalizado com sucesso: {output_file}")
    print("📁 O arquivo foi salvo como .mp4 (internamente ainda é .ts).")

if __name__ == "__main__":
    main()
