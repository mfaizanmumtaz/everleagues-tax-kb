pipeline {
    agent any

    stages {
        stage('Deploy FastAPI Backend') {
            steps {
                echo 'Deploying FastAPI backend with uv and .venv'

                // Sync code to server
                sh '''
                sudo rsync -avz --delete \
                  --exclude ".git" \
                  --exclude ".env" \
                  --exclude "Jenkinsfile" \
                  /var/lib/jenkins/workspace/eltaxdevsvcserver-py-be/ \
                  elaitaxdevadmin@4.193.192.34:/var/www/eltaxdevsvcserver-py-be/
                '''

                // SSH into server and handle venv + dependencies + restart
sh '''
sudo ssh -o StrictHostKeyChecking=no elaitaxdevadmin@4.193.192.34 << 'EOF'
set -e

export PATH=$HOME/.local/bin:$PATH

cd /var/www/eltaxdevsvcserver-py-be

# Create venv if not exists
if [ ! -d ".venv" ]; then
    uv venv .venv
fi

# Activate
source .venv/bin/activate

# Install deps
uv sync

# Ensure gunicorn
uv add gunicorn

# Restart app
pm2 restart eltaxdevsvcserver-py

EOF
'''

            }
        }
    }

    post {
        success {
            emailext(
                body: 'FastAPI Backend successfully deployed. Please verify API is working.',
                subject: '$PROJECT_NAME - Build #$BUILD_NUMBER - SUCCESS!',
                to: 'ghani.waheed@xevensolutions.com'
            )
        }
        failure {
            emailext(
                attachLog: true,
                body: 'FastAPI Backend deployment failed. Please check Jenkins logs.',
                subject: '$PROJECT_NAME - Build #$BUILD_NUMBER - FAILED!',
                to: 'ghani.waheed@xevensolutions.com'
            )
        }
    }
}




