graph [
  name "topology"
  node [
    id 0
    label "node-a"
    resource [
      cpu 32
      memory 8192
      storage 1000
    ]
    zones [
      Zone_X 1
      Zone_Y 0
    ]
    pdc 1
    capability [
      ssd 0
      gpu 0
    ]
    pods [
      Pod_1 [
        demand [
          cpu 1
          memory 100
          storage 10
          ssd 0
          gpu 0
        ]
        prefer [
          cpu 2
          memory 200
          storage 10
          ssd 1
          gpu 0
        ]
        zone "Zone_X"
        collocated 1
        metadata [
          name "Pod_1"
        ]
      ]
    ]
    metadata [
      name "Node_A"
      ip "192.168.0.1"
      architecture "amd64"
      os "Linux"
    ]
  ]
  node [
    id 1
    label "node-b"
    resource [
      cpu 64
      memory 10240
      storage 1000
    ]
    zones [
      Zone_X 1
      Zone_Y 1
    ]
    pdc 0
    capability [
      ssd 1
      gpu 1
    ]
    pods [
    ]
    metadata [
      name "Node_B"
      ip "192.168.0.2"
      architecture "amd64"
      os "Linux"
    ]
  ]
  edge [
    source 0
    target 1
    delay 10
    bw 100
  ]
]
