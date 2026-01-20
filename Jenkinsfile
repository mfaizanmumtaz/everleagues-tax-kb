pipeline {
    agent any

    stages {
        stage('Deploy') {
            steps {
                echo 'Deploying FastAPI backend using uv and .venv'

                // Copy backend source code to server
                sh '''
                sudo rsync -avz --delete \
                --exclude ".git" \
                --exclude ".env" \
                --exclude "Jenkinsfile" \
                /var/lib/jenkins/workspace/eltaxdevsvcserver-py-be/ \
                elaitaxdevadmin@4.193.192.34:/var/www/eltaxdevsvcserver-py-be/
                '''

                // SSH into server and deploy
                sh '''
                sudo ssh -o StrictHostKeyChecking=no elaitaxdevadmin@4.193.192.34 "
                  set -e
                  cd /var/www/eltaxdevsvcserver-py-be

                  echo 'Checking uv...'
                  if ! command -v uv &> /dev/null; then
                    echo 'Installing uv...'
                    pip install --user uv
                  fi

                  # Add local bin to PATH so uv is found
                  export PATH=~/.local/bin:$PATH

                  echo 'Checking for virtual environment...'
                  if [ ! -d .venv ]; then
                    echo 'Creating new .venv environment...'
                    uv venv .venv
                  fi

                  echo 'Activating virtual environment...'
                  source .venv/bin/activate

                  echo 'Syncing dependencies...'
                  uv sync

                  echo 'Installing extra dependencies...'
                  uv add uvicorn gunicorn xmltodict

                  echo 'Restarting FastAPI app via PM2...'
                  pm2 restart eltaxdevsvcserver-py
                "
                '''
            }
        }
    }

    post {
        success {
            emailext (
                body: 'FastAPI Backend successfully deployed. Please verify API is working.',
                subject: '$PROJECT_NAME - Build #$BUILD_NUMBER - SUCCESS!',
                to: ''
            )
        }
        failure {
            emailext (
                attachLog: true,
                body: 'FastAPI Backend deployment failed. Please check Jenkins logs.',
                subject: '$PROJECT_NAME - Build #$BUILD_NUMBER - FAILED!',
                to: 'ghani.waheed@xevensolutions.com'
            )
        }
    }
}
