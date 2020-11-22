pipeline {
    agent any
    stages {
        stage('Install') {
            steps {
                sh 'poetry config repositories.sbt http://192.168.1.11:8081'
                // We use python 3.8 for now due to a bug in pylint.
                // See https://github.com/PyCQA/pylint/issues/3882
                sh 'poetry env use 3.8'
                // Install the dependencies in poetry's virtual environment
                sh 'poetry install'
            }
        }
        stage('Quality Assurance') {
            parallel {
                stage('Test') {
                    environment {
                        // Generate JUnit XML files that jenkins can parse in a
                        // later step (see [1]).
                        PYTEST_ARGS='--junitxml=junit-{envname}.xml'
                    }
                    steps {
                        // Note that we don't do "poetry run tox". This is because
                        // tox manages its own virtual environments. See the
                        // [tool.tox] section in pyproject.toml for details.
                        sh 'python3 -m tox'
                    }
                }
                stage('Lint') {
                    steps {
                        // This runs inside poetry's virtual environment.
                        // Note that we lint both the "cyto" and "tests" directories.
                        sh 'poetry run pylint cyto tests'
                    }
                }
                stage('Type check') {
                    steps {
                        // This runs inside poetry's virtual environment.
                        // Note that we check both the "cyto" and "tests" directories.
                        sh 'poetry run mypy cyto tests'
                    }
                }
            }
        }
        stage('Build') {
            steps {
                sh 'poetry build'
            }
        }
        stage('Publish') {
            environment {
                POETRY_HTTP_BASIC_SBT_USERNAME=credentials('pypiserver-username')
                POETRY_HTTP_BASIC_SBT_PASSWORD=credentials('pypiserver-password')
            }
            steps {
                sh 'poetry publish -r sbt'
            }
        }
    }
    post {
        always {
            junit 'junit-*.xml'  // [1]
        }
    }
}
