from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import time
import os

# IP do servidor: Deixe como "0.0.0.0" para escutar em todas as interfaces de rede disponíveis.
# O ESP32 deve ser configurado para enviar alertas para o IP específico do seu PC na rede local (ex: 172.22.0.7).
HOST_NAME = "0.0.0.0" 
PORT_NUMBER = 8080 # Deve ser a mesma porta configurada no ESP32

class AlertHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        if parsed_path.path == "/alert":
            alert_type = query_params.get("type", [None])[0]
            client_address = self.client_address[0]
            
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ALERTA RECEBIDO de {client_address}!")
            if alert_type:
                print(f"  Tipo de Alerta: {alert_type}")
            else:
                print("  Tipo de Alerta: Não especificado")

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Alerta recebido pelo servidor Python!")
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Endpoint nao encontrado.")

if __name__ == "__main__":
    # Garante que estamos no diretório certo se o script for movido
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # print(f"Servidor rodando no diretório: {script_dir}") # Descomente se precisar depurar o diretório

    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), AlertHandler)
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"))
    print(f"Servidor de Alerta iniciado em http://{HOST_NAME}:{PORT_NUMBER}")
    print(f"Esperando por alertas do ESP32 no IP do seu PC ({PORT_NUMBER}/alert?type=...)")
    print("Pressione Ctrl+C para parar o servidor.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print(time.strftime("[%Y-%m-%d %H:%M:%S]") + " Servidor parado.") 