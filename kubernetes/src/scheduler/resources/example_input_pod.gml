graph [
  name "pod"
  node [
    id 0
    label "pod"
    demand [
      cpu 4000
      memory 200000
      storage 0
      ssd 0
      gpu 1
    ]
    prefer [
      cpu 8000
      memory 1000000
      storage 0
      ssd 1
      gpu 1
    ]
    zone "_networkx_list_start"
    zone "Zone_Y"
    collocated 0
    metadata [
      name "Pod_2"
    ]
  ]
]
