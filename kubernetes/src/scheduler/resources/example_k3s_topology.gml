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
    zone [
      default 1
      zone_A 1
      zone_B 1
    ]
    pdc 1
    capability [
      ssd 0
      gpu 1
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
        zone [
          default 1
        ]
        collocated 0
        metadata [
          name "scheduler"
          namespace "ptx-edge"
          created "2025-12-01T13:40:20Z"
          scheduler "default-scheduler"
          status "Running"
          labels [
            app "scheduler"
          ]
        ]
      ]
    ]
    metadata [
      name "k3d-dev-agent-0"
      architecture "amd64"
      os "linux"
      kernel "6.8.0-87-generic"
      ip "172.21.0.3"
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
    zone [
      default 1
    ]
    pdc 0
    capability [
      ssd 1
      gpu 0
    ]
    pod [
    ]
    metadata [
      name "k3d-dev-server-0"
      architecture "amd64"
      os "linux"
      kernel "6.8.0-87-generic"
      ip "172.21.0.2"
    ]
  ]
]
