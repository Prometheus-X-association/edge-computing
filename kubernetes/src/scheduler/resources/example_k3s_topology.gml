graph [
  name "topology"
  node [
    id 0
    label "k3d-dev-agent-0"
    resource [
      cpu 4000
      memory 5035316
      storage 95904111
    ]
    capacity [
      cpu 4000
      memory 5035316
      storage 95904111
    ]
    zone "default"
    zone "zone-A"
    zone "zone-B"
    pdc 1
    capability [
      ssd 0
      gpu 1
    ]
    pod [
    ]
    metadata [
      api_version "v1"
      kind "Node"
      name "k3d-dev-agent-0"
      resource_version "755"
      uid "c7559d4c-9b82-4f4b-a7bb-110e854f1f35"
      info [
        architecture "amd64"
        os "linux"
        kernel "6.8.0-88-generic"
        ip "172.21.0.3"
      ]
    ]
  ]
  node [
    id 1
    label "k3d-dev-server-0"
    resource [
      cpu 4000
      memory 5035316
      storage 95904111
    ]
    capacity [
      cpu 4000
      memory 5035316
      storage 95904111
    ]
    zone "_networkx_list_start"
    zone "default"
    pdc 0
    capability [
      ssd 1
      gpu 0
    ]
    pod [
      scheduler [
        priority 0
        demand [
          cpu 0
          memory 0
          storage 0
          ssd 0
          gpu 0
        ]
        prefer [
          cpu 0
          memory 0
          storage 0
          ssd 0
          gpu 0
        ]
        zone "_networkx_list_start"
        zone "default"
        collocated 0
        metadata [
          api_version "v1"
          kind "Pod"
          name "scheduler"
          namespace "ptx-edge"
          resource_version "796"
          uid "9df1eea3-bbb1-4e5d-9c1a-cc457c3ebaaa"
          labels [
            app "scheduler"
          ]
          info [
            creation_timestamp "2025-12-10T11:19:54Z"
            node "k3d-dev-server-0"
            scheduler "default-scheduler"
            status "Running"
            ip "10.42.1.6"
          ]
        ]
      ]
    ]
    metadata [
      api_version "v1"
      kind "Node"
      name "k3d-dev-server-0"
      resource_version "806"
      uid "c5c38b5d-30d9-444f-a9ef-007b42694746"
      info [
        architecture "amd64"
        os "linux"
        kernel "6.8.0-88-generic"
        ip "172.21.0.2"
      ]
    ]
  ]
]
