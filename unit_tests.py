from kubernetes import client, config, watch
from kubernetes.client.exceptions import ApiException
from podinfo_controller import create_podinfo_deployment, update_podinfo_deployment, delete_podinfo_deployment

# Unit Tests
config.load_kube_config()

core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
custom_api = client.CustomObjectsApi()

def test_create_podinfo_deployment():
    namespace = 'default'
    spec = {
        'replicaCount': 2,
        'image': {'repository': 'stefanprodan/podinfo', 'tag': 'latest'},
        'ui': {'color': '#34577c', 'message': 'Welcome to Podinfo!'},
        'env': [{'name': 'PODINFO_UI_COLOR', 'value': '#34577c'}, {'name': 'PODINFO_UI_MESSAGE', 'value': 'Welcome to Podinfo!'}],
    }
    create_podinfo_deployment(spec, namespace)
    deployment = apps_v1.read_namespaced_deployment('podinfo', namespace)
    assert deployment.spec.replicas == spec['replicaCount']
    assert deployment.spec.template.spec.containers[0].image == f"{spec['image']['repository']}:{spec['image']['tag']}"

def test_update_podinfo_deployment():
    namespace = 'default'
    new_spec = {
        'replicaCount': 3,
        'image': {'repository': 'stefanprodan/podinfo', 'tag': 'new-version'},
        'ui': {'color': '#123456', 'message': 'Updated Message'},
        'env': [{'name': 'PODINFO_UI_COLOR', 'value': '#34577c'}, {'name': 'PODINFO_UI_MESSAGE', 'value': 'Welcome to Podinfo!'}],
    }
    update_podinfo_deployment(new_spec, namespace)
    deployment = apps_v1.read_namespaced_deployment('podinfo', namespace)
    assert deployment.spec.replicas == new_spec['replicaCount']
    assert deployment.spec.template.spec.containers[0].image == f"{new_spec['image']['repository']}:{new_spec['image']['tag']}"

def test_delete_podinfo_deployment():
    namespace = 'default'
    delete_podinfo_deployment(namespace)
    try:
        apps_v1.read_namespaced_deployment('podinfo', namespace)
        assert False, "Deployment should be deleted"
    except ApiException as e:
        assert e.status == 404

if __name__ == "__main__":
    test_create_podinfo_deployment()
    test_update_podinfo_deployment()
    test_delete_podinfo_deployment()
