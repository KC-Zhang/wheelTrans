# wheelTrans
## mac installation guide 

# install docker
https://docs.docker.com/desktop/install/mac-install/


# deploy code
the project is hosted on gcp , project elderlyHomeTransportation

to deploy:
    run docker locally 
    
    docker buildx create --use
    docker buildx build --platform linux/amd64 -t gcr.io/elderlyhometransportation/sc-wheel-trans:amd64 --output type=docker . 
    (simply running docker build -t sc-wheel-trans . won't work because the remote machine is amd64 )


    push to docker registry 
        gcloud auth login
        gcloud config set project elderlyhometransportation
        gcloud auth configure-docker
        docker push gcr.io/elderlyhometransportation/sc-wheel-trans:amd64

    gcp restart the vm

# how to use it
     go to http://35.247.7.127:80 

https://www.notion.so/kaichengzhang/sc-wheel-trans-397c24e01d3e470680979981251aa673