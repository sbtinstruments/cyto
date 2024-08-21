pipeline {
    agent {
        dockerfile {
            filename 'Dockerfile.build'
        }
    }
    stages {
        stage('Install') {
            steps {
                // Install all extras along with the dependencies in
                // poetry's virtual environment.
                sh 'poetry install --all-extras'
            }
        }
        stage('Quality assurance') {
            parallel {
                stage('Lint (ruff)') {
                    steps {
                        sh 'poetry run task ruff'
                    }
                }
                stage('Check types (mypy)') {
                    steps {
                        sh 'poetry run task mypy'
                    }
                }
            }
        }
        stage('Quality control') {
            stages {
                stage('Test (pytest)') {
                    steps {
                        sh 'poetry run pytest --junitxml=junit.xml'
                    }
                    post {
                        always {
                            // Parse JUnit XML files
                            junit 'junit.xml'
                        }
                    }
                }
                stage('Coverage (pytest-cov)') {
                    environment {
                        // Get total coverage for the badge
                        TOTAL_COVERAGE=sh(script: 'poetry run pytest --cov=cyto tests | grep TOTAL | awk \'{print $4 "\\t"}\'', returnStdout: true).trim()
                    }
                    steps {
                        sh ''
                    }
                    post {
                        always {
                            addShortText text: "Coverage: ${env.TOTAL_COVERAGE}"
                        }
                    }
                }
            }
        }
        stage('Build') {
            steps {
                sh 'poetry build'
            }
        }
    }
}
