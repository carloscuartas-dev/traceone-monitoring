#!/bin/bash
# TraceOne Monitoring API - Postman Test Runner Script
# This script runs comprehensive API tests using Newman (Postman CLI)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
POSTMAN_DIR="$PROJECT_ROOT/postman"

# Test configurations
COLLECTION_FILE="$POSTMAN_DIR/TraceOne_Monitoring_API.postman_collection.json"
ENVIRONMENT_FILE="$POSTMAN_DIR/TraceOne_Environments.postman_environment.json"
REPORTS_DIR="$PROJECT_ROOT/test-reports"

# Ensure reports directory exists
mkdir -p "$REPORTS_DIR"

echo -e "${BLUE}🚀 TraceOne Monitoring API Test Runner${NC}"
echo "=================================================="

# Check if Newman is installed
check_newman() {
    if ! command -v newman &> /dev/null; then
        echo -e "${RED}❌ Newman is not installed${NC}"
        echo -e "${YELLOW}Installing Newman...${NC}"
        npm install -g newman
        echo -e "${GREEN}✅ Newman installed successfully${NC}"
    else
        echo -e "${GREEN}✅ Newman is available${NC}"
    fi
}

# Check if collection and environment files exist
check_files() {
    if [[ ! -f "$COLLECTION_FILE" ]]; then
        echo -e "${RED}❌ Collection file not found: $COLLECTION_FILE${NC}"
        exit 1
    fi
    
    if [[ ! -f "$ENVIRONMENT_FILE" ]]; then
        echo -e "${RED}❌ Environment file not found: $ENVIRONMENT_FILE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Postman files found${NC}"
}

# Run basic API tests
run_basic_tests() {
    echo -e "${BLUE}🧪 Running Basic API Tests${NC}"
    echo "----------------------------------"
    
    newman run "$COLLECTION_FILE" \
        -e "$ENVIRONMENT_FILE" \
        --reporters cli,json,html \
        --reporter-json-export "$REPORTS_DIR/basic-test-results.json" \
        --reporter-html-export "$REPORTS_DIR/basic-test-report.html" \
        --timeout-request 30000 \
        --delay-request 1000 \
        --folder "Authentication" \
        --folder "Health Checks"
}

# Run registration workflow tests
run_registration_tests() {
    echo -e "${BLUE}📝 Running Registration Workflow Tests${NC}"
    echo "----------------------------------------"
    
    newman run "$COLLECTION_FILE" \
        -e "$ENVIRONMENT_FILE" \
        --reporters cli,json,html \
        --reporter-json-export "$REPORTS_DIR/registration-test-results.json" \
        --reporter-html-export "$REPORTS_DIR/registration-test-report.html" \
        --timeout-request 30000 \
        --delay-request 1000 \
        --folder "Authentication" \
        --folder "Registration Management" \
        --folder "DUNS Management" \
        --folder "Monitoring Control"
}

# Run notification workflow tests
run_notification_tests() {
    echo -e "${BLUE}📬 Running Notification Workflow Tests${NC}"
    echo "---------------------------------------"
    
    newman run "$COLLECTION_FILE" \
        -e "$ENVIRONMENT_FILE" \
        --reporters cli,json,html \
        --reporter-json-export "$REPORTS_DIR/notification-test-results.json" \
        --reporter-html-export "$REPORTS_DIR/notification-test-report.html" \
        --timeout-request 30000 \
        --delay-request 1000 \
        --folder "Authentication" \
        --folder "Pull API"
}

# Run complete end-to-end tests
run_e2e_tests() {
    echo -e "${BLUE}🔄 Running End-to-End Tests${NC}"
    echo "------------------------------"
    
    newman run "$COLLECTION_FILE" \
        -e "$ENVIRONMENT_FILE" \
        --reporters cli,json,html,junit \
        --reporter-json-export "$REPORTS_DIR/e2e-test-results.json" \
        --reporter-html-export "$REPORTS_DIR/e2e-test-report.html" \
        --reporter-junit-export "$REPORTS_DIR/e2e-junit-report.xml" \
        --timeout-request 30000 \
        --delay-request 1500 \
        --bail
}

# Run performance tests
run_performance_tests() {
    echo -e "${BLUE}⚡ Running Performance Tests${NC}"
    echo "------------------------------"
    
    newman run "$COLLECTION_FILE" \
        -e "$ENVIRONMENT_FILE" \
        --reporters cli,json \
        --reporter-json-export "$REPORTS_DIR/performance-test-results.json" \
        --timeout-request 10000 \
        --delay-request 500 \
        -n 5 \
        --folder "Authentication" \
        --folder "Health Checks" \
        --folder "Pull API"
}

# Run load tests
run_load_tests() {
    echo -e "${BLUE}🔥 Running Load Tests${NC}"
    echo "----------------------"
    
    newman run "$COLLECTION_FILE" \
        -e "$ENVIRONMENT_FILE" \
        --reporters cli,json \
        --reporter-json-export "$REPORTS_DIR/load-test-results.json" \
        --timeout-request 15000 \
        --delay-request 2000 \
        -n 10 \
        --folder "Authentication" \
        --folder "Pull API"
}

# Generate test summary
generate_summary() {
    echo -e "${BLUE}📊 Test Summary${NC}"
    echo "=================="
    
    if [[ -f "$REPORTS_DIR/e2e-test-results.json" ]]; then
        echo "Parsing test results..."
        
        # Extract key metrics using jq if available
        if command -v jq &> /dev/null; then
            TOTAL_TESTS=$(jq '.run.stats.tests.total' "$REPORTS_DIR/e2e-test-results.json")
            PASSED_TESTS=$(jq '.run.stats.tests.passed' "$REPORTS_DIR/e2e-test-results.json")
            FAILED_TESTS=$(jq '.run.stats.tests.failed' "$REPORTS_DIR/e2e-test-results.json")
            
            echo -e "Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
            echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
            echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
            
            if [[ "$FAILED_TESTS" -eq 0 ]]; then
                echo -e "\n${GREEN}🎉 All tests passed!${NC}"
            else
                echo -e "\n${RED}❌ Some tests failed. Check the reports for details.${NC}"
            fi
        fi
    fi
    
    echo -e "\n📁 Reports generated in: ${YELLOW}$REPORTS_DIR${NC}"
    echo "   - HTML Reports: Open *.html files in browser"
    echo "   - JSON Reports: Machine-readable results"
    echo "   - JUnit Reports: For CI/CD integration"
}

# Main execution
main() {
    echo -e "${YELLOW}Starting TraceOne API Tests...${NC}\n"
    
    # Pre-flight checks
    check_newman
    check_files
    
    # Parse command line arguments
    case "${1:-all}" in
        "basic")
            run_basic_tests
            ;;
        "registration")
            run_registration_tests
            ;;
        "notification")
            run_notification_tests
            ;;
        "e2e")
            run_e2e_tests
            ;;
        "performance")
            run_performance_tests
            ;;
        "load")
            run_load_tests
            ;;
        "all")
            run_basic_tests
            sleep 2
            run_registration_tests
            sleep 2
            run_notification_tests
            sleep 2
            run_e2e_tests
            ;;
        *)
            echo "Usage: $0 [basic|registration|notification|e2e|performance|load|all]"
            echo ""
            echo "Test Types:"
            echo "  basic        - Authentication and health checks"
            echo "  registration - Registration management workflow"
            echo "  notification - Notification pulling workflow"
            echo "  e2e          - Complete end-to-end tests"
            echo "  performance  - Performance testing (5 iterations)"
            echo "  load         - Load testing (10 iterations)"
            echo "  all          - Run all core tests (default)"
            exit 1
            ;;
    esac
    
    # Generate summary
    generate_summary
    
    echo -e "\n${GREEN}✅ Test execution completed${NC}"
}

# Run with error handling
trap 'echo -e "\n${RED}❌ Test execution failed${NC}"; exit 1' ERR

main "$@"
