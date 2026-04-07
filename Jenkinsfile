pipeline {
    agent {
        docker {
            image 'python:3.11'
            args '-u root -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git submodule update --init --recursive'
            }
        }

        stage('Init') {
            steps {
                sh '''
                    python3 -m pip install --upgrade pip setuptools wheel
                    python3 -m pip install pipenv
                    command -v pipenv
                    docker --version
                '''
                sh 'PIPENV_PIPFILE=config/Pipfile pipenv install --dev'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'make ci-unit-test'
            }
        }

        stage('Integration Tests') {
            steps {
                sh 'make ci-integration-test'
            }
        }

        stage('E2E Tests') {
            steps {
                sh 'make e2e-up'
                sh 'make e2e-test'
            }
            post {
                always {
                    sh 'make e2e-logs || true'
                    sh 'make e2e-down || true'
                }
            }
        }
    }

    post {
        always {
            sh 'make docker-down || true'
            sh '''
                for sys in systems/*/; do
                    [ -f "$sys/Makefile" ] && make -C "$sys" docker-down PROJECT_ROOT="$(pwd)" 2>/dev/null || true
                done
            '''
        }
    }
}
