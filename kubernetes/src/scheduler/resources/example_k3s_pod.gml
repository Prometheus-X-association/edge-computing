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
      storage 0
      ssd 0
      gpu 0
    ]
    zone [
      zone_A 1
    ]
    collocated 1
    metadata [
      name "test"
      namespace "ptx-edge"
      created "2025-12-01T14:34:36Z"
      scheduler "ptx-edge-scheduler"
      status "Pending"
      labels [
        app "worker"
      ]
    ]
  ]
]
