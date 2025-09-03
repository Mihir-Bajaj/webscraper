#!/bin/bash

# Docker management script for webscraper API
# Usage: ./docker.sh [build|start|stop|restart|logs|status|clean|shell]

COMPOSE_FILE="docker-compose.yml"
SERVICE_NAME="webscraper-api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
}

# Function to build the image
build_image() {
    print_status "Building webscraper API Docker image..."
    check_docker
    
    if docker-compose -f "$COMPOSE_FILE" build; then
        print_status "Docker image built successfully!"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to start services
start_services() {
    print_status "Starting webscraper services..."
    check_docker
    
    if docker-compose -f "$COMPOSE_FILE" up -d; then
        print_status "Services started successfully!"
        print_info "API: http://localhost:8000"
        print_info "API docs: http://localhost:8000/docs"
        print_info "Database: localhost:5432"
        print_info "View logs: ./docker.sh logs"
    else
        print_error "Failed to start services"
        exit 1
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping webscraper services..."
    check_docker
    
    if docker-compose -f "$COMPOSE_FILE" down; then
        print_status "Services stopped successfully!"
    else
        print_error "Failed to stop services"
        exit 1
    fi
}

# Function to restart services
restart_services() {
    print_status "Restarting webscraper services..."
    stop_services
    sleep 2
    start_services
}

# Function to show logs
show_logs() {
    print_status "Showing service logs (Ctrl+C to exit):"
    check_docker
    
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Function to show status
show_status() {
    print_status "Checking service status..."
    check_docker
    
    echo -e "\n${BLUE}Container Status:${NC}"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo -e "\n${BLUE}API Health Check:${NC}"
    if curl -s "http://localhost:8000/" > /dev/null 2>&1; then
        print_status "API is responding"
        curl -s "http://localhost:8000/" | jq . 2>/dev/null || curl -s "http://localhost:8000/"
    else
        print_warning "API is not responding"
    fi
    
    echo -e "\n${BLUE}Database Status:${NC}"
    if docker-compose -f "$COMPOSE_FILE" exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        print_status "Database is ready"
    else
        print_warning "Database is not ready"
    fi
}

# Function to clean up
clean_up() {
    print_status "Cleaning up Docker resources..."
    check_docker
    
    print_warning "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
        docker system prune -f
        print_status "Cleanup completed!"
    else
        print_info "Cleanup cancelled"
    fi
}

# Function to access shell
access_shell() {
    print_status "Accessing container shell..."
    check_docker
    
    if docker-compose -f "$COMPOSE_FILE" exec "$SERVICE_NAME" /bin/bash; then
        print_status "Shell session ended"
    else
        print_error "Failed to access shell"
    fi
}

# Function to test API
test_api() {
    print_status "Testing API endpoints..."
    
    echo -e "\n${BLUE}Root endpoint:${NC}"
    curl -s "http://localhost:8000/" | jq . 2>/dev/null || curl -s "http://localhost:8000/"
    
    echo -e "\n${BLUE}Health check:${NC}"
    curl -s "http://localhost:8000/health" | jq . 2>/dev/null || curl -s "http://localhost:8000/health"
    
    echo -e "\n${BLUE}Available endpoints:${NC}"
    curl -s "http://localhost:8000/openapi.json" | jq '.paths | keys' 2>/dev/null || echo "Could not fetch endpoints"
}

# Main script logic
case "${1:-}" in
    "build")
        build_image
        ;;
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "clean")
        clean_up
        ;;
    "shell")
        access_shell
        ;;
    "test")
        test_api
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|status|logs|clean|shell|test}"
        echo ""
        echo "Commands:"
        echo "  build   - Build Docker image"
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show service status"
        echo "  logs    - Show service logs"
        echo "  clean   - Clean up Docker resources"
        echo "  shell   - Access container shell"
        echo "  test    - Test API endpoints"
        echo ""
        echo "Examples:"
        echo "  ./docker.sh build    # Build image"
        echo "  ./docker.sh start    # Start services"
        echo "  ./docker.sh status   # Check status"
        echo "  ./docker.sh test     # Test API"
        echo "  ./docker.sh logs     # View logs"
        echo "  ./docker.sh stop     # Stop services"
        ;;
esac 