from aiida.orm import Node
from aiida.common.datastructures import calc_states
from aiida.common.exceptions import ModificationNotAllowed

#TODO: set the following as properties of the Calculation
#        'email',
#        'email_on_started',
#        'email_on_terminated',
#        'rerunnable',
#        'queue_name', 
#        'num_machines',
#        'priority',
#        'resourceLimits',

_input_subfolder = 'raw_input'

class Calculation(Node):
    _updatable_attributes = ('state', 'job_id', 'scheduler_state',
                             'last_jobinfo', 'remote_workdir', 'retrieve_list')
    
    def __init__(self,*args,**kwargs):
        """
        Possible arguments:
        computer, num_machines, num_cpus_per_machine, code
        """
        super(Calculation,self).__init__(*args, **kwargs)

        uuid = kwargs.pop('uuid', None)
        if uuid is not None:
            # if I am loading an existing calc: stop here
            return

        # For new calculations
        self._set_state(calc_states.NEW)
        self.set_label("Calculation {}".format(self.uuid))

        computer = kwargs.pop('computer', None)
        if computer is not None:
            self.set_computer(computer)

        num_machines = kwargs.pop('num_machines',None)
        if num_machines is not None:
            self.set_num_machines(num_machines)        

        num_cpus_per_machine = kwargs.pop('num_cpus_per_machine',None)
        if num_cpus_per_machine is not None:
            self.set_num_cpus_per_machine(num_cpus_per_machine)        

        if kwargs:
            raise ValueError("Invalid parameters found in the __init__: "
                             "{}".format(kwargs.keys()))

    def validate(self):
        from aiida.common.exceptions import ValidationError
        
        super(Calculation,self).validate()

        if self.get_computer() is None:
            raise ValidationError("You did not specify any computer")

        if self.get_state() not in calc_states:
            raise ValidationError("Calculation state '{}' is not valid".format(
                self.get_state()))

        try:
            if int(self.get_num_machines()) <= 0:
                raise ValueError
        except (ValueError,TypeError):
            raise ValidationError("The number of machines must be specified "
                                  "and must be positive")

        try:
            if int(self.get_num_cpus_per_machine()) <= 0:
                raise ValueError
        except (ValueError,TypeError):
            raise ValidationError("The number of CPUs per machine must be "
                                  "specified and must be positive")

    def can_link_as_output(self,dest):
        """
        Raise a ValueError if a link from self to dest is not allowed.
        
        An output of a calculation can only be a data, and can only be set 
        when the calculation is in the SUBMITTING or RETRIEVING or
        PARSING state.
        (during SUBMITTING, the execmanager adds a link to the remote folder; 
         all other links are added while in the retrieving phase)
        """
        from aiida.orm import Data

        valid_states = [
              calc_states.SUBMITTING,
              calc_states.RETRIEVING,
              calc_states.PARSING,
              ]
        
        if not isinstance(dest, Data):
            raise ValueError(
                "The output of a calculation node can only be a data node")

        if self.get_state() not in valid_states:
            raise ModificationNotAllowed(
                "Can add an output node to a calculation only if it is in one "
                "of the following states: {}, it is instead {}".format(
                    valid_states, self.get_state()))

        return super(Calculation, self).can_link_as_output(dest)

    def _store_raw_input_folder(self, folder_path):
        """
        Copy the content of the folder internally, in a subfolder called
        'raw_input'

        Args:
            folder_path: the path to the folder from which the content
                should be taken
        """
        # This function can be called only if the state is SUBMITTING
        if self.get_state() != calc_states.SUBMITTING:
            raise ModificationNotAllowed(
                "The raw input folder can be stored only if the "
                "state is SUBMITTING, it is instead {}".format(
                    self.get_state()))

        # get subfolder and replace with copy
        raw_input_folder = self.current_folder.get_subfolder(
            _input_subfolder,create=True)
        raw_input_folder.replace_with_folder(
            folder_path, move=False, overwrite=True)

    @property
    def raw_input_folder(self):
        from aiida.common.exceptions import NotExistent

        return_folder = self.current_folder.get_subfolder(_input_subfolder)
        if return_folder.exists():
            return return_folder
        else:
            raise NotExistent("raw_input_folder not created yet")

    def set_queue_name(self,val):
        self.set_attr('queue_name',unicode(val))

    def set_priority(self,val):
        self.set_attr('priority',unicode(val))
    
    def set_max_memory_kb(self,val):
        self.set_attr('max_memory_kb',int(val))

    def set_max_wallclock_seconds(self,val):    
        self.set_attr('max_wallclock_seconds',int(val))

    def set_num_machines(self,val):
        self.set_attr('num_machines',int(val))

    def set_num_cpus_per_machine(self,val):
        self.set_attr('num_cpus_per_machine',int(val))

    def get_queue_name(self):
        return self.get_attr('queue_name', None)

    def get_priority(self):
        return self.get_attr('priority', None)
    
    def get_max_memory_kb(self):
        return self.get_attr('max_memory_kb', None)

    def get_max_wallclock_seconds(self):	
        return self.get_attr('max_wallclock_seconds', None)

    def get_num_machines(self):
        return self.get_attr('num_machines', None)

    def get_num_cpus_per_machine(self):
        return self.get_attr('num_cpus_per_machine', None)
        
    def add_link_from(self,src,label=None):
        '''
        Add a link with a code as destination.
        You can use the parameters of the base Node class, in particular the
        label parameter to label the link.
        '''
        
        from aiida.orm.data import Data
        from aiida.orm.code import Code
        
        
        if not isinstance(src,(Data, Code)):
            raise ValueError("Nodes entering in calculation can only be of "
                             "type data or code")
        
        valid_states = [calc_states.NEW]

        if self.get_state() not in valid_states:
            raise ModificationNotAllowed(
                "Can add an input node to a calculation only if it is in one "
                "of the following states: {}, it is instead {}".format(
                    valid_states, self.get_state()))

        return super(Calculation,self).add_link_from(src, label)

    def set_computer(self,computer):
        """
        TODO: probably this method should be in the base class, and
        check for the type
        """
        from aiida.djsite.db.models import DbComputer

        if self._to_be_stored:
            self.dbnode.computer = DbComputer.get_dbcomputer(computer)
        else:
            self.logger.error("Trying to change the computer of an already "
                              "saved node: {}".format(self.uuid))
            raise ModificationNotAllowed(
                "Node with uuid={} was already stored".format(self.uuid))

    def get_computer(self):
        from aiida.orm import Computer
        return Computer(dbcomputer=self.dbnode.computer)

    def _set_state(self, state):
        if state not in calc_states:
            raise ValueError(
                "'{}' is not a valid calculation status".format(state))
        self.set_attr('state', state)

    def get_state(self):
        return self.get_attr('state', None)

    def _set_remote_workdir(self, remote_workdir):
        if self.get_state() != calc_states.SUBMITTING:   
            raise ModificationNotAllowed(
                "Cannot set the remote workdir if you are not "
			    "submitting the calculation (current state is "
				"{})".format(self.get_state()))
        self.set_attr('remote_workdir', remote_workdir)

    def get_remote_workdir(self):
        return self.get_attr('remote_workdir', None)

    def _set_retrieve_list(self, retrieve_list):
        if self.get_state() != calc_states.SUBMITTING:
            raise ModificationNotAllowed(
                "Cannot set the retrieve_list if you are not "
				"submitting the calculation (current state is "
		        "{})".format(self.get_state()))

        if (not(isinstance(retrieve_list,(tuple,list))) or
	           not(all(isinstance(i,basestring) for i in retrieve_list))):
            raise ValueError("You have to pass a list (or tuple) of strings "
                             "as retrieve_list")
        self.set_attr('retrieve_list', retrieve_list)

    def get_retrieve_list(self):
        return self.get_attr('retrieve_list', None)

    def _set_job_id(self, job_id):
        """
        Always set as a string
        """
        if self.get_state() != calc_states.SUBMITTING:
            raise ModificationNotAllowed("Cannot set the job id if you are not "
					 "submitting the calculation (current state is "
					 "{})".format(self.get_state()))

        return self.set_attr('job_id', unicode(job_id))
    
    def get_job_id(self):
        return self.get_attr('job_id', None)
        
    def _set_scheduler_state(self,state):
        # I don't do any test here on the possible valid values,
        # I just convert it to a string
        self.set_attr('scheduler_state', unicode(state))
                
    def get_scheduler_state(self):
        return self.get_attr('scheduler_state', None)

    def _set_last_jobinfo(self,last_jobinfo):
        import pickle
        
        self.set_attr('last_jobinfo', pickle.dumps(last_jobinfo))

    def get_last_jobinfo(self):
        import pickle
        
        last_jobinfo_pickled = self.get_attr('last_jobinfo',None)
        if last_jobinfo_pickled is not None:
            return pickle.loads(last_jobinfo_pickled)
        else:
            return None
    

    @classmethod
    def get_all_with_state(cls, state, computer=None, user=None, 
                           only_computer_user_pairs = False):
        """
        Filter all calculations with a given state.

        Issue a warning if the state is not in the list of valid states.

        Args:
            state: The state to be used to filter (should be a string among 
                those defined in aiida.common.datastructures.calc_states)
            computer: a Django DbComputer entry, or a Computer object, of a
                computer in the DbComputer table.
                A string for the hostname is also valid.
            user: a Django entry (or its pk) of a user in the User table;
                if present, the results are restricted to calculations of that
                specific user
            only_computer_user_pairs: if False (default) return a queryset 
                where each element is a suitable instance of Node (it should
                be an instance of Calculation, if everything goes right!)
                If True, return only a list of tuples, where each tuple is
                in the format
                ('computer__id', 'user__id')
                [where the IDs are the IDs of the respective tables]
        """
        # I assume that calc_states are strings. If this changes in the future,
        # update the filter below from attributes__tval to the correct field.
        from aiida.orm import Computer

        if state not in calc_states:
            cls.logger.warning("querying for calculation state='{}', but it "
                "is not a valid calculation state".format(state))

        kwargs = {}
        if computer is not None:
            # I convert it from various type of inputs
            # (string, DbComputer, Computer)
            # to a Computer type
            kwargs['computer'] = Computer.get(computer)
        if user is not None:
            kwargs['user'] = user
        
        queryresults = cls.query(
            attributes__key='_state',
            attributes__tval=state,
            **kwargs)

        if only_computer_user_pairs:
            return queryresults.values_list(
                'computer__id', 'user__id')
        else:
            return queryresults

    def use_code(self, code):
        """
        Set the code for this calculation
        """
        from aiida.orm import Code

        if not isinstance(code, Code):
            raise ValueError("The code must be an instance of the Code class")

        self.replace_link_from(code, self.get_linkname_code())
        
    def get_linkname_code(self):
        """
        The name of the link used for the code
        """
        return "code"
        
    def _prepare_for_submission(self,tempfolder):        
        """
        This is the routine to be called when you want to create
        the input files and related stuff with a plugin.
        
        Args:
            tempfolder: a aiida.common.folders.Folder subclass where
                the plugin should put all its files.

        TODO: document what it has to return (probably a CalcInfo object)
              and what is the behavior on the tempfolder
        """
        raise NotImplementedError

    def submit(self):
        """
        Submit the calculation.
        """ 
        from aiida.execmanager import submit_calc
        
        submit_calc(self)

#       output_plugin = kwargs.pop('output_plugin', None)
#       self.set_output_plugin(output_plugin)

#    def set_output_plugin(self, output_plugin):
#        """
#        Set a string for the output plugin
#        Can be none if no output plugin is available/needed
#
#        TODO: check that the plugin referenced by th string input_plugin actually exists
#        """
#        self.set_attr('output_plugin', output_plugin)


## SOME OLD COMMENTS
# Each calculation object should be defined by analogy of a function 
# with a fixed set of labeled and declared inputs.
# 
# mystruc = Struc(...)
# myinputparam = InputParam(...)
# myjobparam = JobParam(...)
# myupfA = UPF(...)
# myupfB = UPF(...)
# 
# MyCalc = Calc({'struc': Struc(), 'upfA': UPF(),...})
# This will define the abstract object with labeled input ports of defined type. 
# 
# MyCalc({'struc':mystruc, 'upfA':myupfA, ...})
# 
# Calculations can exist in the db as empty entities of state 'Abstract'.
# Also Data can exist in the db with 'Abstract' state. This can be used to pre-define a workflow.
# 
# Calculation can only be submitted if all the data inputs are filled with concrete data objects.
# It then changes status to 'Prepared' and so on.
# Note: a calculation is set to 'retrieved' when all output nodes are validated and stored (TBD). 
# 
# When dealing with workflows g(f(A,B),C) = h(A,B,C)
# however g(f(A,B=5),C) = h(A,C) since B is concrete.
# 
# To repeat an existing (static) workflow, take the set of calculation nodes, 
# copy them and related data nodes and set everything to abstract. Then run throught the static workflow manager.
# User can choose new data inputs.
# 
# A dynamic workflow is a script that creates calc and data on the fly. 
# The script can be stored as an attribute of a previously generated workflow.
# Here each calculation needs to be hashed in order to be reused on restarts.
# 
# NOTE: Need to include functionality of an observer method in calc or data plugins, to check the data 
# while the calculation is running, to make sure that everything is going as planned, otherwise stop.