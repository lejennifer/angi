# angi

Assumes user is running macOS, has Minikube and python3 installed, has Docker running

Create a virtual environment

`python3 -m venv <your_virtual_env_dir>`

Activate virtual env

`. <your_virtual_env_dir>/bin/activate`

Install requirements.txt

`pip install -r requirements.txt`

Testing with Minikube

```
minikube start
eval $(minikube docker-env)
```

Apply CRD

`kubectl apply -f podinfo_crd.yaml`

Run the controller

`python podinfo_controller.py &`

Make changes to myappresource.yaml

```
  ui:
    color: "#34577c"
    message: "change me"
```

Reapply the resource

`kubectl apply -f myappresource.yaml`

Run port-forward to view your changes:

`kubectl port-forward deployment/podinfo 8080:9898 -n default`

View on browser

`localhost:8080`

Run tests

`pytest unit_tests.py`

Stop Minikube

`minikube stop`
