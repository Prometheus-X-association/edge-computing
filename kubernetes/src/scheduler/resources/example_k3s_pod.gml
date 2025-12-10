graph [
  name "pod"
  node [
    id 0
    label "test"
    priority 0
    demand [
      cpu 100
      memory 92160
      storage 0
      ssd 0
      gpu 0
    ]
    prefer [
      cpu 500
      memory 317440
      storage 102400
      ssd 0
      gpu 0
    ]
    zone "_networkx_list_start"
    zone "zone-A"
    collocated 1
    metadata [
      api_version "v1"
      kind "Pod"
      name "test"
      namespace "ptx-edge"
      resource_version "817"
      uid "d1e6574e-d05a-40df-99d7-da71ce269865"
      labels [
        app "worker"
      ]
      info [
        creation_timestamp "2025-12-10T11:20:25Z"
        node ""
        scheduler "ptx-edge-scheduler"
        status "Pending"
        ip ""
      ]
    ]
  ]
]
