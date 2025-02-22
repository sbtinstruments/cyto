pipeline {
    agent {
        dockerfile {
            filename 'Dockerfile.build'
        }
    }
    stages {
        stage('Install') {
            steps {
                sh 'uv sync --all-extras'
            }
        }
        stage('Quality assurance') {
            parallel {
                stage('Lint (ruff)') {
                    steps {
                        sh 'uv run task ruff'
                    }
                }
                stage('Check types (mypy)') {
                    steps {
                        sh 'uv run task mypy'
                    }
                }
            }
        }
        stage('Quality control') {
            stages {
                stage('Test (pytest)') {
                    steps {
                        sh 'uv run pytest --junitxml=junit.xml'
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
                        TOTAL_COVERAGE=sh(script: 'uv run pytest --cov=cyto tests | grep TOTAL | awk \'{print $4 "\\t"}\'', returnStdout: true).trim()
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
                sh 'uv build'
            }
        }
    }
}
