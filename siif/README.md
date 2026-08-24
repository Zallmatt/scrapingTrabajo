# Copa Gastos SIIF

Actualiza los reportes **rf604m**, **rf610m** y **rf610mfte** desde SIIF y carga los datos a la base (UPSERT).

## Uso diario (recomendado)

1. En la PC de oficina, con **Wi‑Fi de red interna** y **Chrome** instalado.
2. Doble clic en el acceso del escritorio **Actualizar Copa Gastos**.
3. Cuando abra Chrome: completá el **captcha** y hacé clic en **Ingresar**.
4. Dejá correr la ventana; no hace falta tocar nada más (puede tardar varias horas).

Si el acceso no está en el escritorio, instalalo una vez:

```powershell
powershell -ExecutionPolicy Bypass -File siif\instalar_acceso_escritorio.ps1
```

También podés abrir `siif\ActualizarCopaGastos.bat` directamente.

## Requisitos

- Python 3 con el launcher `py`
- Dependencias del repo (`requirements.txt`)
- Archivo `.env` en la raíz del repo (credenciales SIIF y base de datos)
- Red con acceso a `siif.cgpc.gob.ar`

## Comandos avanzados

Desde la raíz del repo:

```text
# Todo (descarga + transform + UPSERT) — igual que el bat
py -3 -u siif/run_all_gastos.py

# Solo descarga
py -3 -u siif/run_all_gastos.py --solo-descarga

# Solo transform + carga (si ya están los .xls)
py -3 -u siif/run_all_gastos.py --solo-carga

# Continuar desde un reporte
py -3 -u siif/run_all_gastos.py --solo-descarga --desde rf610m

# Un reporte puntual
py -3 -u siif/run_all_gastos.py --solo-descarga --solo rf610mfte

# Prueba corta (1 entidad, enero 2025)
py -3 -u siif/run_all_gastos.py --test
```

## Tablas

| Reporte    | Tabla               |
|------------|---------------------|
| rf604m     | `copa_gastos`       |
| rf610m     | `copa_gastos_nuevo` |
| rf610mfte  | `copa_gastos_fte`   |

Los `.xls` ya descargados se saltan; la carga es UPSERT (no trunca).
