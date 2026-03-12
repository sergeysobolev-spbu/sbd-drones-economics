pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Init') {
            steps {
                sh 'command -v pipenv >/dev/null 2>&1 || pip install pipenv'
                sh 'PIPENV_PIPFILE=config/Pipfile pipenv install --dev'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'make unit-test'
            }
        }

        stage('Integration Tests') {
            steps {
                sh 'make tests'
            }
        }
    }

    post {
        always {
            sh 'make docker-down || true'
        }
    }
}