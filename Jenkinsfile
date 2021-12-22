pipeline {
    agent {
        dockerfile {
            filename 'Dockerfile.build'
        }
    }
    stages {
        stage('Install') {
            steps {
                // Use a local poetry virtual environment. E.g., inside a
                // .venv folder in the workspace itself. This way, Jenkins
                // can clear poetry's virtual environment before each build.
                // E.g., with the "wipe out repository" or "clean before
                // checkout" option.
                sh 'poetry config --local virtualenvs.in-project true'
                // We use python 3.8 for now due to a bug in pylint.
                // See https://github.com/PyCQA/pylint/issues/3882
                sh 'poetry env use 3.8'
                // Install all extras along with the dependencies in
                // poetry's virtual environment.
                sh 'poetry install --extras all'
            }
        }
        stage('Quality Assurance') {
            parallel {
                stage('Test') {
                    environment {
                        // The spinner interferes with Jenkins' output parsing.
                        TOX_PARALLEL_NO_SPINNER=1
                        // Generate JUnit XML files that Jenkins can parse in a
                        // post section (see [1]).
                        PYTEST_ARGS='--junitxml=junit-{envname}.xml'
                    }
                    stages {
                        stage('pytest') {
                            environment {
                                // We skip the coverage step for now. We run this in
                                // test environment later in its own stage.
                                TOX_SKIP_ENV='coverage'
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
                                }
                            }
                        }
                        stage('coverage') {
                            steps {
                                // Note that we don't do "poetry run tox". This is because
                                // tox manages its own virtual environments. See the
                                // [tool.tox] section in pyproject.toml for details.
                                sh 'python3 -m tox --parallel -e coverage'
                            }
                            post {
                                always {
                                    // Publish the HTML coverage report
                                    publishHTML target: [
                                        // Report may be missing if one of the tests fail
                                        allowMissing: true,
                                        alwaysLinkToLastBuild: true,
                                        keepAll: true,
                                        reportDir: 'htmlcov',
                                        reportFiles: 'index.html',
                                        reportName: 'Test Coverage Report'
                                    ]
                                }
                            }
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
    }
    post {
        failure {
            // Notify slack if anything went wrong
            slackSend(color: '#FF9FA1', message: "`${env.JOB_NAME}` has failed CI:\n${env.BUILD_URL}")
        }
    }
}
