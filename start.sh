#!/bin/bash

# Script para levantar la aplicación Flask con Docker Compose

echo "🚀 Iniciando aplicación Flask con Docker Compose..."
echo "================================================"

# Verificar si Docker está ejecutándose
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está ejecutándose"
    echo "   Por favor inicia Docker y vuelve a intentar"
    exit 1
fi

# Verificar si docker-compose está disponible
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose no está instalado"
    echo "   Por favor instala docker-compose y vuelve a intentar"
    exit 1
fi

# Limpiar contenedores anteriores (opcional)
echo "🧹 Limpiando contenedores anteriores..."
docker-compose down --remove-orphans

# Construir y levantar servicios
echo "🔨 Construyendo imágenes..."
docker-compose build --no-cache

echo "🚀 Levantando servicios..."
docker-compose up -d

# Esperar a que los servicios estén listos
echo "⏳ Esperando a que los servicios estén listos..."
sleep 10

# Verificar estado de los servicios
echo "📊 Estado de los servicios:"
docker-compose ps

# Mostrar logs en tiempo real
echo ""
echo "📝 Logs de la aplicación (Ctrl+C para detener los logs):"
echo "========================================================="
echo ""
echo "🌐 URLs disponibles:"
echo "   - Aplicación: http://localhost:87"
echo "   - Flask directo: http://localhost:5000"
echo "   - InfluxDB: http://localhost:8087"
echo "   - Documentación: http://localhost:87/endpoints-page"
echo ""
echo "📋 Comandos útiles:"
echo "   - Ver logs: docker-compose logs -f"
echo "   - Parar servicios: docker-compose down"
echo "   - Reiniciar: docker-compose restart"
echo ""

# Mostrar logs de todos los servicios
docker-compose logs -f