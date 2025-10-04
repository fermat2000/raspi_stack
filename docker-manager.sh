#!/bin/bash

# Script de manejo de Docker Compose para la aplicación Flask

case "$1" in
    start)
        echo "🚀 Iniciando servicios..."
        docker-compose up -d
        echo "✅ Servicios iniciados!"
        echo ""
        echo "📋 URLs disponibles:"
        echo "   🌐 Aplicación principal: http://localhost:87"
        echo "   🐳 Flask directo: http://localhost:5000"
        echo "   📊 InfluxDB: http://localhost:8087"
        echo "   📋 Documentación: http://localhost:87/endpoints-page"
        ;;
    stop)
        echo "🛑 Parando servicios..."
        docker-compose down
        echo "✅ Servicios parados!"
        ;;
    restart)
        echo "🔄 Reiniciando servicios..."
        docker-compose down
        docker-compose up -d
        echo "✅ Servicios reiniciados!"
        ;;
    rebuild)
        echo "🔨 Reconstruyendo y reiniciando..."
        docker-compose down
        docker-compose build
        docker-compose up -d
        echo "✅ Servicios reconstruidos y reiniciados!"
        ;;
    logs)
        echo "📝 Mostrando logs..."
        docker-compose logs -f
        ;;
    status)
        echo "📊 Estado de los servicios:"
        docker-compose ps
        ;;
    *)
        echo "🐳 Docker Compose Manager para Flask App"
        echo ""
        echo "Uso: $0 {start|stop|restart|rebuild|logs|status}"
        echo ""
        echo "Comandos:"
        echo "  start    - Iniciar todos los servicios"
        echo "  stop     - Parar todos los servicios"
        echo "  restart  - Reiniciar todos los servicios"
        echo "  rebuild  - Reconstruir imágenes y reiniciar"
        echo "  logs     - Mostrar logs en tiempo real"
        echo "  status   - Mostrar estado de los servicios"
        echo ""
        echo "URLs cuando esté corriendo:"
        echo "  🌐 http://localhost:87 - Aplicación principal"
        echo "  🐳 http://localhost:5000 - Flask directo"
        echo "  📊 http://localhost:8087 - InfluxDB"
        echo "  📋 http://localhost:87/endpoints-page - Documentación"
        exit 1
        ;;
esac