from waitress import serve

from app import *

if __name__ == '__main__':    
    local_host, local_port = '0.0.0.0', 8080
    print(f'\nServindo em {local_host}:{local_port}')
    serve(app, host=local_host, port=local_port)
    
