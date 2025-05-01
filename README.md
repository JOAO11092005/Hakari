cat << 'EOF' > README.md
# 🎥 Hakari - Downloader e Uploader Automático de Vídeos .m3u8 para Cloudflare R2

**Hakari** é uma poderosa ferramenta Python projetada para baixar vídeos a partir de playlists `.m3u8` e fazer upload automático para o armazenamento **Cloudflare R2**. Ideal para automações de mídia, arquivamento de conteúdo e integração com serviços baseados em HLS (HTTP Live Streaming).

---

## 🚀 Funcionalidades

- 📥 **Download Automático de .m3u8**  
  Seleciona automaticamente a melhor qualidade disponível (resoluções ≥ 720p) e baixa todos os segmentos `.ts`.

- 📦 **Merge de Segmentos**  
  Junta os arquivos baixados em um único `.mp4` local.

- ☁️ **Upload para Cloudflare R2**  
  Upload com barra de progresso e link público gerado automaticamente.

- 🔄 **Automação Completa**  
  Desde a coleta do link até o envio para a nuvem, tudo acontece com um único comando.

---

## 🛠️ Instalação

Não requer configuração manual de dependências — o script se encarrega disso automaticamente:

```bash
python3 app.py
