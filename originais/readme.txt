=== DEPENDENCIAS ===
Rode o código no Powershell em modo admin:
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install pymodbus>=3.5 pandas>=2.0 numpy>=1.24 scikit-learn>=1.3 matplotlib>=3.7

=== INICIALIZAR O SERVIDOR ===
python servidor.py --host 0.0.0.0 --port 5020

=== INICIALIZAR O CLIENTE ===
python cliente.py --host 127.0.0.1 --port 5020 --csv dados.csv --intervalo 1