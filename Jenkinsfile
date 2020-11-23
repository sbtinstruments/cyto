pipeline {
    agent any
    stages {
        stage('Install') {
            steps {
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
                        // The spinner interferes with Jenkins' output parsing.
                        TOX_PARALLEL_NO_SPINNER=1
                        // Generate JUnit XML files that jenkins can parse in a
                        // post (see [1]).
                        PYTEST_ARGS='--junitxml=junit-{envname}.xml'
                    }
                    steps {
                        // Note that we don't do "poetry run tox". This is because
                        // tox manages its own virtual environments. See the
                        // [tool.tox] section in pyproject.toml for details.
                        sh 'python3 -m tox --parallel'
                    }
                    post {
                        always {
                            // Parse JUnit XML files
                            junit 'junit-*.xml'  // [1]
                            // Publish the HTML coverage report
                            publishHTML target: [
                                // Report may be missing if one of the tests fail
                                allowMissing: true,
                                alwaysLinkToLastBuild: false,
                                keepAll: true,
                                reportDir: 'htmlcov',
                                reportFiles: 'index.html',
                                reportName: 'Test Coverage Report'
                            ]
                        }
                    }
                }
                stage('Lint') {
                    steps {
                        // This runs inside poetry's virtual environment.
                        sh 'poetry run task pylint'
                    }
                }
                stage('Check types') {
                    steps {
                        // This runs inside poetry's virtual environment.
                        sh 'poetry run task mypy'
                    }
                }
                stage('Check formatting') {
                    steps {
                        // This runs inside poetry's virtual environment.
                        sh 'poetry run task black --check'
                    }
                }
                stage('Check import order') {
                    steps {
                        // This runs inside poetry's virtual environment.
                        sh 'poetry run task isort --check'
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
                // Just use the local pypiserver for now.
                TWINE_REPOSITORY_URL='http://127.0.0.1:8081'
                TWINE_USERNAME=credentials('pypiserver-username')
                TWINE_PASSWORD=credentials('pypiserver-password')
            }
            steps {
                // Note that we don't use `poetry publish`. It simply doesn't
                // work for non-interactive use. We got "Prompt dismissed.." errors.
                // Instead, we use twine for now.
                sh 'python3 -m twine check dist/*'
                sh 'python3 -m twine upload --skip-existing dist/*'
            }
        }
    }
}
