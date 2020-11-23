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
                        // Generate JUnit XML files that jenkins can parse in a
                        // later step (see [1]).
                        PYTEST_ARGS='--junitxml=junit-{envname}.xml'
                    }
                    steps {
                        script {
                            def envs = sh(returnStdout: true, script: "tox -l").trim().split('\n')
                            def cmds = envs.collectEntries({ tox_env ->
                                [tox_env, {
                                    sh "python3 -m tox --parallel--safe-build -vve $tox_env"
                                }]
                            })
                            parallel(cmds)
                        }
                        // Note that we don't do "poetry run tox". This is because
                        // tox manages its own virtual environments. See the
                        // [tool.tox] section in pyproject.toml for details.
                        //sh 'python3 -m tox'
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
    post {
        always {
            junit 'junit-*.xml'  // [1]
        }
    }
}
