import os
from kubernetes import client, config, watch
from kubernetes.client.exceptions import ApiException

config.load_kube_config()

core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
custom_api = client.CustomObjectsApi()

GROUP = "podinfo.interview.assignment"
VERSION = "v1alpha1"
PLURAL = "myappresources"
NAMESPACE = "default"

def create_redis_secret(namespace):
    secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name='redis-password'),
        string_data={'password': 'your-secure-password'}
    )
    try:
        core_v1.create_namespaced_secret(namespace, secret)
        print("Secret created successfully")
    except ApiException as e:
        if e.status == 409:
            print("Secret already exists, skipping creation")
        else:
            print("Error creating secret:", e)

def create_podinfo_deployment(spec, namespace):
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name='podinfo'),
        spec=client.V1DeploymentSpec(
            replicas=spec['replicaCount'],
            selector=client.V1LabelSelector(
                match_labels={"app": "podinfo"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "podinfo"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name='podinfo',
                            image=f"{spec['image']['repository']}:{spec['image']['tag']}",
                            env=[
                                client.V1EnvVar(name='PODINFO_UI_COLOR', value=spec['ui']['color']),
                                client.V1EnvVar(name='PODINFO_UI_MESSAGE', value=spec['ui']['message']),
                                client.V1EnvVar(name='PODINFO_CACHE_SERVER', value='tcp://<host>:<port>')
                            ]
                        )
                    ]
                )
            )
        )
    )
    try:
        apps_v1.create_namespaced_deployment(namespace, deployment)
    except ApiException as e:
        if e.status == 409:
            print("Deployment already exists, updating instead")
            update_podinfo_deployment(spec, namespace)
        else:
            raise



def delete_podinfo_deployment(namespace):
    apps_v1.delete_namespaced_deployment('podinfo', namespace)


def update_podinfo_deployment(spec, namespace, max_retries=3):
    for _ in range(max_retries):
        try:
            existing_deployment = apps_v1.read_namespaced_deployment('podinfo', namespace)
            existing_deployment.spec.replicas = spec['replicaCount']
            existing_deployment.spec.template.spec.containers[0].image = f"{spec['image']['repository']}:{spec['image']['tag']}"
            existing_deployment.spec.template.spec.containers[0].env[0].value = spec['ui']['color']
            existing_deployment.spec.template.spec.containers[0].env[1].value = spec['ui']['message']
            apps_v1.replace_namespaced_deployment('podinfo', namespace, existing_deployment)
            return
        except ApiException as e:
            if e.status == 409:
                print("Conflict while updating deployment. Retrying...")
            else:
                raise


def handle_event(event_type, event_object):
    namespace = event_object['metadata']['namespace']
    spec = event_object['spec']

    if event_type == "ADDED":
        # Handle Redis secret
        if spec.get('redis', {}).get('enabled'):
            create_redis_secret(namespace)
        # Deploy podinfo application
        create_podinfo_deployment(spec, namespace)

    elif event_type == "MODIFIED":
        update_podinfo_deployment(spec, namespace)

    elif event_type == "DELETED":
        # Delete podinfo deployment
        delete_podinfo_deployment(namespace)


def main():
    resource_version = ""
    while True:
        stream = watch.Watch().stream(
            custom_api.list_cluster_custom_object,
            GROUP, VERSION, PLURAL,
            resource_version=resource_version
        )
        for event in stream:
            resource_version = event['object']['metadata']['resourceVersion']
            handle_event(event['type'], event['object'])


if __name__ == "__main__":
    main()

# Unit Tests

def test_create_podinfo_deployment():
    namespace = 'default'
    spec = {
        'replicaCount': 2,
        'image': {'repository': 'stefanprodan/podinfo', 'tag': 'latest'},
        'ui': {'color': '#34577c', 'message': 'Welcome to Podinfo!'}
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
        'ui': {'color': '#123456', 'message': 'Updated Message'}
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