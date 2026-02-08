"""
Script para probar la conexión al servidor Asterisk remoto
"""
import socket
import sys

class AsteriskConnectionTest:
    def __init__(self, host, port=5038, username='admin', password=''):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sock = None
    
    def _send_command(self, command):
        """Enviar comando al AMI"""
        if self.sock:
            self.sock.sendall(command.encode('utf-8'))
    
    def _read_response(self, timeout=5):
        """Leer respuesta del AMI"""
        self.sock.settimeout(timeout)
        response = b''
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                # Buscar fin de mensaje AMI
                if b'\r\n\r\n' in response:
                    break
        except socket.timeout:
            pass
        except Exception as e:
            print(f"❌ Error leyendo respuesta: {e}")
        
        return response.decode('utf-8', errors='ignore')
    
    def test_connection(self):
        """Probar conexión al AMI"""
        print(f"\n{'='*60}")
        print(f"  PRUEBA DE CONEXIÓN ASTERISK AMI")
        print(f"{'='*60}\n")
        
        print(f"🔌 Intentando conectar a {self.host}:{self.port}...")
        
        try:
            # Crear socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            
            # Conectar
            self.sock.connect((self.host, self.port))
            print(f"✅ Conexión TCP establecida\n")
            
            # Leer banner de bienvenida
            banner = self._read_response()
            print(f"📋 Banner de Asterisk:")
            print(f"{banner}")
            
            # Autenticarse
            print(f"🔐 Autenticando como '{self.username}'...")
            login_cmd = f"Action: Login\r\nUsername: {self.username}\r\nSecret: {self.password}\r\n\r\n"
            self._send_command(login_cmd)
            
            login_response = self._read_response()
            print(f"📨 Respuesta de login:")
            print(f"{login_response}")
            
            if 'Success' in login_response or 'authentication accepted' in login_response.lower():
                print(f"\n✅ AUTENTICACIÓN EXITOSA\n")
                
                # Obtener información del sistema
                self._test_commands()
                
                # Logout
                print(f"\n🚪 Desconectando...")
                self._send_command("Action: Logoff\r\n\r\n")
                self.sock.close()
                
                print(f"\n{'='*60}")
                print(f"  ✅ CONEXIÓN EXITOSA - Asterisk está funcionando")
                print(f"{'='*60}\n")
                return True
            else:
                print(f"\n❌ ERROR DE AUTENTICACIÓN")
                print(f"Verifica usuario y contraseña en manager.conf")
                return False
                
        except socket.timeout:
            print(f"\n❌ TIMEOUT: No se pudo conectar a {self.host}:{self.port}")
            print(f"   El servidor podría estar inaccesible o el puerto bloqueado")
            return False
        except ConnectionRefusedError:
            print(f"\n❌ CONEXIÓN RECHAZADA: {self.host}:{self.port}")
            print(f"   Verifica que Asterisk esté ejecutándose")
            print(f"   Verifica que el AMI esté habilitado en manager.conf")
            return False
        except socket.gaierror as e:
            print(f"\n❌ ERROR DE DNS: No se puede resolver '{self.host}'")
            print(f"   {e}")
            return False
        except Exception as e:
            print(f"\n❌ ERROR INESPERADO: {e}")
            return False
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
    
    def _test_commands(self):
        """Probar algunos comandos AMI básicos"""
        print(f"\n{'─'*60}")
        print(f"  PROBANDO COMANDOS AMI")
        print(f"{'─'*60}\n")
        
        commands = [
            ("CoreStatus", "Action: CoreStatus\r\n\r\n"),
            ("SIP Peers", "Action: SIPpeers\r\n\r\n"),
            ("PJSIP Endpoints", "Action: PJSIPShowEndpoints\r\n\r\n"),
        ]
        
        for name, cmd in commands:
            try:
                print(f"📤 Ejecutando: {name}")
                self._send_command(cmd)
                response = self._read_response()
                
                # Mostrar primeras líneas de la respuesta
                lines = response.split('\r\n')
                for line in lines[:10]:
                    if line.strip():
                        print(f"   {line}")
                
                if len(lines) > 10:
                    print(f"   ... ({len(lines)} líneas totales)")
                print()
            except Exception as e:
                print(f"   ⚠️  Error: {e}\n")


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("  HERRAMIENTA DE DIAGNÓSTICO ASTERISK AMI")
    print("="*60 + "\n")
    
    # Solicitar datos de conexión
    print("Ingresa los datos del servidor Asterisk:\n")
    
    host = input("Host/IP del servidor Asterisk: ").strip()
    if not host:
        print("❌ El host es obligatorio")
        return
    
    port_str = input("Puerto AMI [5038]: ").strip()
    port = int(port_str) if port_str else 5038
    
    username = input("Usuario AMI [admin]: ").strip()
    if not username:
        username = 'admin'
    
    password = input("Contraseña AMI: ").strip()
    
    # Crear tester y probar conexión
    tester = AsteriskConnectionTest(host, port, username, password)
    success = tester.test_connection()
    
    if success:
        print("\n💡 SIGUIENTE PASO:")
        print("   Actualiza el archivo .env con estos valores:")
        print(f"\n   ASTERISK_HOST={host}")
        print(f"   ASTERISK_AMI_PORT={port}")
        print(f"   ASTERISK_AMI_USER={username}")
        print(f"   ASTERISK_AMI_PASSWORD={password}\n")
    else:
        print("\n🔧 SOLUCIONES POSIBLES:")
        print("   1. Verifica que Asterisk esté ejecutándose:")
        print("      ssh user@servidor 'asterisk -rx \"core show version\"'")
        print("\n   2. Verifica que el AMI esté habilitado en /etc/asterisk/manager.conf:")
        print("      [general]")
        print("      enabled = yes")
        print("      bindaddr = 0.0.0.0")
        print("      port = 5038")
        print(f"\n   3. Verifica que exista el usuario '{username}' en manager.conf:")
        print(f"      [{username}]")
        print("      secret = tu_contraseña")
        print("      deny = 0.0.0.0/0.0.0.0")
        print("      permit = 0.0.0.0/0.0.0.0")
        print("      read = system,call,log,verbose,command,agent,user,config")
        print("      write = system,call,log,verbose,command,agent,user,config")
        print("\n   4. Verifica reglas de firewall:")
        print(f"      sudo ufw allow {port}/tcp")
        print("\n   5. Recarga la configuración de Asterisk:")
        print("      asterisk -rx 'manager reload'\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Prueba cancelada por el usuario\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
